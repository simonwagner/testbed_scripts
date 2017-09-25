SCRIPT="$( basename "${BASH_SOURCE[0]}" )"

RSYNC_OPT="--info=progress2 --no-inc-recursive -acz -e ssh --delete"

for host in $HOSTS; do
  echo "[$SCRIPT] Uploading support scripts to $host:$REMOTE_SUPPORT_DIR..."
  ssh $host "mkdir -p $REMOTE_SUPPORT_DIR"
  rsync $RSYNC_OPT ${SUPPORT_DIR} $host:$REMOTE_SUPPORT_DIR
done