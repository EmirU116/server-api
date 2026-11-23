# Discord alerts on Ubuntu EC2 (G6)

The host collector stores measurements for the dashboard. A separate check
runs about once a minute and sends a Discord message if the root filesystem
reaches the configured usage threshold. The message names the host, usage, and
threshold. This check works with the native or container deployment.

## Configure the alert (Discord, Bash, systemd)

1. In the target Discord server, open **Server Settings → Integrations →
   Webhooks**. Create a webhook for the alerts text channel and copy its URL privately.
2. On EC2, save the URL to a private file in your SSH user's home directory.
   The prompt hides your input. Keep the URL out of Git and the recording.

   ```bash
   umask 077
   install -d -m 700 "$HOME/.config/serverwatch-alerts"
   if IFS= read -rsp 'Discord webhook URL: ' webhook; then
       printf '%s\n' "$webhook" > "$HOME/.config/serverwatch-alerts/discord-webhook"
   fi
   unset webhook
   printf '\n'
   chmod 600 "$HOME/.config/serverwatch-alerts/discord-webhook"
   ```

3. In the cloned repository, run the installer as the Ubuntu SSH user.

   ```bash
   bash infrastructure/bootstrap/setup_discord_alerts.sh "$HOME/.config/serverwatch-alerts/discord-webhook" 90
   systemctl list-timers serverwatch-discord.timer
   sudo journalctl -u serverwatch-discord.service -n 20 --no-pager
   ```

   The installer copies the webhook to a root-only file under
   `/etc/serverwatch-discord/`, and systemd grants the checker temporary
   access to the credential for each run. The EC2 instance needs outbound
   HTTPS to Discord. The alert code uses Python 3's standard library.

## Prove that the scheduled check sends an alert (EC2, Discord)

1. Run `df -h /` and pick a whole-number test threshold between 1 and 100
   below the displayed usage. For example, with normal usage around 12%,
   pick 5%.
2. Rerun the installer with the test threshold in place of 90. Wait for
   the timer and confirm one message appears. Check the journal again
   after another run to verify that the same breach is suppressed.
3. Rerun the installer with 90 or your normal threshold. When the usage is
   next below that threshold, the checker rearms for a future breach.

If the journal reports a delivery failure, check the webhook again and confirm
EC2 can reach Discord. The next scheduled check retries while disk usage is
still high. If Discord accepted a request but the connection failed before
confirmation, a retry can send a duplicate.

The checker waits for Discord to confirm message creation. [Discord webhook reference](https://docs.discord.com/developers/resources/webhook#execute-webhook)
