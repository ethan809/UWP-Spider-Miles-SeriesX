// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using SpiderManInstaller.SteamTransfer;

namespace SpiderManInstaller
{
    internal static class SteamDownload
    {
        static readonly SemaphoreSlim Gate = new SemaphoreSlim(1);
        internal static async Task RunAsync(string localFolder, List<ExpectedFile> expected, long freeBytes,
            Action<string> status, Action<string> qr, CancellationToken token,
            Action<DownloadProgressSnapshot> progress = null, int workers = 4,
            SteamLoginCredentials credentials = null, ISteamGuardPrompt guardPrompt = null,
            string language = "english", bool languageOnly = false, bool milesDownloadOnly = false)
        {
            if (!await Gate.WaitAsync(0)) throw new InvalidOperationException("A Steam download is already running.");
            SteamSession session = null;
            Timer pulse = null;
            TransferTrace trace = null;
            try
            {
                token.ThrowIfCancellationRequested();
                if (milesDownloadOnly && (languageOnly || language != "english"))
                    throw new InvalidDataException("Miles Morales download currently supports English only.");
                if (!milesDownloadOnly) SteamLanguages.Depots(language,languageOnly); // Reject unknown IDs before using a path or connecting.
                string folder = milesDownloadOnly ? Path.Combine(localFolder, "MilesMoralesSteam") :
                    languageOnly ? Path.Combine(localFolder,"SteamLanguages",language) : Path.Combine(localFolder, "SteamDownload");
                Directory.CreateDirectory(folder);
                if (milesDownloadOnly)
                {
                    string priorReceipt = TransferCore.FullPath(folder, "miles-steam-verified.txt");
                    if (File.Exists(priorReceipt)) File.Delete(priorReceipt);
                }
                trace = new TransferTrace(Path.Combine(localFolder, milesDownloadOnly ? "miles-steam-transfer.log" : "steam-transfer.log"));
                if (!milesDownloadOnly && (expected == null || expected.Count == 0))
                    throw new InvalidDataException("Supported game-file list is missing.");
                if (!milesDownloadOnly)
                {
                    long requiredBeforeLogin = TransferCore.RequiredFreeSpace(folder, expected);
                    if (freeBytes < requiredBeforeLogin) throw new TransferProblem("Need " + (requiredBeforeLogin / 1073741824.0).ToString("F1") + " GiB free for download and safe replacement.");
                }
                string receipt = TransferCore.FullPath(folder, "import-receipt.txt");
                if (!languageOnly && !milesDownloadOnly && File.Exists(receipt)) File.Delete(receipt);
                var tracker = new DownloadProgressTracker(progress ?? (p => { }));
                if (!milesDownloadOnly) tracker.Begin(expected.Sum(f => f.Size));
                pulse = new Timer(_ => tracker.Pulse(), null, 1000, 1000);
                session = new SteamSession(new SteamMachineIdentity(), trace, token,
                    milesDownloadOnly ? SteamSession.MilesAppId : 1817070);
                status(credentials==null?"Approve the QR sign-in in your Steam app.":"Signing in to Steam. Complete Steam Guard if requested.");
                await session.Login(qr,credentials,guardPrompt).ConfigureAwait(false);
                tracker.Stage("Checking supported Steam version");
                status(milesDownloadOnly ? "Checking your Miles Morales license and current Steam manifests..." :
                    "Checking access to supported build 14752622...");
                var plan = milesDownloadOnly ? await session.ReadMilesPlan(token).ConfigureAwait(false) :
                    await session.ReadPlan(expected, token,language,languageOnly).ConfigureAwait(false);
                if (milesDownloadOnly)
                {
                    expected = plan.Select(p => p.Expected).ToList();
                    long required = TransferCore.RequiredFreeSpace(folder, expected);
                    if (freeBytes < required)
                        throw new TransferProblem("Miles Morales needs " + (required / 1073741824.0).ToString("F1") + " GiB free for the Steam download and safe replacement.");
                    tracker.Begin(expected.Sum(f => f.Size));
                }
                int completed = 0;
                foreach (var file in plan)
                {
                    status("Downloading and verifying file " + (completed + 1) + " of " + plan.Count + ".");
                    await TransferCore.DownloadFile(folder, file, Math.Max(2, Math.Min(8, workers)), tracker, token).ConfigureAwait(false);
                    trace.Record(TransferEvent.VerifiedFile, ++completed);
                }
                token.ThrowIfCancellationRequested();
                if (milesDownloadOnly)
                {
                    File.WriteAllText(TransferCore.FullPath(folder, "miles-steam-verified.txt"),
                        "Miles Morales Steam download verified\r\nUTC " + DateTime.UtcNow.ToString("o") +
                        "\r\nFiles " + expected.Count + "\r\nDownload only: no Xbox-compatible game runtime exists in this launcher.\r\n");
                }
                else if (!languageOnly) {
                    File.WriteAllText(receipt, "Verified original Steam files\r\nUTC " + DateTime.UtcNow.ToString("o") +
                        "\r\nFiles " + expected.Count + "\r\nReady for preparation.\r\n");
                    File.WriteAllText(TransferCore.FullPath(folder,SteamLanguages.PreferenceFile),language);
                }
                tracker.Stage("Complete"); trace.Record(TransferEvent.Completed, completed);
                status(milesDownloadOnly ? "Miles Morales Steam files verified. Download only: Miles is not yet playable on Xbox." :
                    languageOnly?"Voice pack downloaded and verified.":"Steam files verified. Choose Prepare game to enable Play.");
            }
            catch (OperationCanceledException) when (token.IsCancellationRequested)
            { trace?.Record(TransferEvent.Cancelled); throw; }
            catch (TransferProblem ex) { trace?.Record(TransferEvent.Failed, failure: ex); throw; }
            catch (Exception ex)
            {
                trace?.Record(TransferEvent.Failed, failure: ex);
                throw new IOException("Steam transfer stopped. Sign in again to retry and resume checked chunks. Error metadata is in " +
                    (milesDownloadOnly ? "miles-steam-transfer.log." : "steam-transfer.log."), ex);
            }
            finally
            {
                credentials?.Dispose();
                pulse?.Dispose();
                try { if (session != null) await session.Close().ConfigureAwait(false); }
                finally { qr(null); Gate.Release(); }
            }
        }
        internal static Task RunMilesAsync(string localFolder, long freeBytes,
            Action<string> status, Action<string> qr, CancellationToken token,
            Action<DownloadProgressSnapshot> progress, int workers,
            SteamLoginCredentials credentials = null, ISteamGuardPrompt guardPrompt = null)
            => RunAsync(localFolder, null, freeBytes, status, qr, token, progress, workers,
                credentials, guardPrompt, "english", false, true);
        internal static void Verify(string folder, ExpectedFile file, CancellationToken token) => TransferCore.Verify(folder, file, token);
    }
}
