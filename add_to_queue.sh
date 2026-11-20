#!/usr/bin/env bash
# Add a video to the posting queue and push it to GitHub.
#   ./add_to_queue.sh <video.mp4> <caption.txt> [short-name]
# Videos are posted one per day, in the order they were added.
set -euo pipefail
cd "$(dirname "$0")"

video=${1:?usage: ./add_to_queue.sh <video.mp4> <caption.txt> [short-name]}
caption=${2:?usage: ./add_to_queue.sh <video.mp4> <caption.txt> [short-name]}
slug=${3:-$(basename "$video" .mp4 | tr '_ ' '--' | tr 'A-Z' 'a-z')}

# Instagram limits: caption up to 2,200 characters and 30 hashtags.
chars=$(wc -m < "$caption")
tags=$(grep -o '#[[:alnum:]_]*' "$caption" | wc -l)
(( chars <= 2200 )) || { echo "Caption is $chars characters; Instagram allows 2,200." >&2; exit 1; }
(( tags <= 30 )) || { echo "Caption has $tags hashtags; Instagram allows 30." >&2; exit 1; }

mkdir -p queue
last=$(find queue -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort | tail -1 | cut -c1-3)
num=$(printf '%03d' $(( 10#${last:-0} + 1 )))
dest="queue/$num-$slug"
mkdir -p "$dest"

# Instagram's API wants AAC audio at 48 kHz or lower; video is copied as is.
ffmpeg -v error -y -i "$video" -c:v copy -ar 48000 -c:a aac -b:a 192k -movflags +faststart "$dest/video.mp4"
cp "$caption" "$dest/caption.txt"

git add "$dest"
git commit -q -m "Queue $num-$slug"
git push -q
echo "Queued as $dest. Waiting in queue: $(( $(find queue -name video.mp4 | wc -l) )) video(s)."
