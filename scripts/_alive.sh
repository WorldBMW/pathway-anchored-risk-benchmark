#!/bin/bash
LOG=/root/autodl-tmp/project/project4_cervix_multimodal/logs/_alive.log
rm -f "$LOG"
for i in $(seq 1 60); do
  echo "tick $i $(date +%s)" >> "$LOG"
  sleep 5
done
echo "ALIVE_DONE" >> "$LOG"
