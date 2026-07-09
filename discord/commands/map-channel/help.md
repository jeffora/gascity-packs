Map a Discord guild channel to a workflow dispatch target.

Example:
  gc discord map-channel 123456789012345678 223456789012345678 product/claude \
    --fix-formula mol-discord-fix-issue

Arguments:
  <guild_id>    Discord guild id
  <channel_id>  Discord parent channel id
  <target>      rig/<pool-worker> sling target (e.g. rig/claude — the rig's
                configured pool worker)

Flags:
  --fix-formula <name>  formula to use for `/gc fix`, default: mol-discord-fix-issue

Thread interactions inherit the mapping from their parent channel.
