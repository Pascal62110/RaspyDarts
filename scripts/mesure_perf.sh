#!/bin/sh
#
# Measures what the running game costs, during one situation of the game
# (menu, waiting for a dart, game in progress...) :
#   sh scripts/mesure_perf.sh <situation> [seconds, 60 by default]
#
# Writes logs/mesure_<situation>_<date>.txt :
# - temperature, clock and throttling of the Pi, before and after
# - mean CPU used by the game (100 % = one full core)
# - the busiest threads of the game, every 5 seconds
# - with py-spy installed (sudo pip3 install --break-system-packages py-spy) : where the
#   game spends its time, in logs/pyspy_<situation>_<date>.svg (to open in a browser)
#
# For the measures made inside the game (time between two reads of the target, time of
# each screen refresh) : touch perf in the game folder, restart the game, then read
# logs/perf.log. rm perf to stop them.

cd "$(dirname "$(readlink -f "$0")")/.."

SITUATION=${1:-mesure}
DURATION=${2:-60}
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="logs/mesure_${SITUATION}_${STAMP}.txt"
mkdir -p logs

PID=$(pgrep -f "raspydarts\.py" | head -n1)
if [ -z "$PID" ]
then
	echo "Le jeu ne tourne pas (pas de processus raspydarts.py)"
	exit 1
fi

pi_state() {
	echo "  $(vcgencmd measure_temp 2> /dev/null)  $(vcgencmd measure_clock arm 2> /dev/null)  $(vcgencmd get_throttled 2> /dev/null)"
}

# utime + stime of the process, in clock ticks (fields 14 and 15 of /proc/PID/stat,
# counted after the name of the process, which may contain spaces)
cpu_ticks() {
	sed -e 's/^.*) //' "/proc/$PID/stat" | awk '{ print $12 + $13 }'
}

{
	echo "Situation : $SITUATION, $DURATION s, $(date)"
	echo "Jeu : PID $PID, mesures internes $( [ -f perf ] && echo actives || echo inactives )"
	echo
	echo "Etat du Pi au debut :"
	pi_state
} > "$OUT"

if command -v py-spy > /dev/null 2>&1
then
	sudo py-spy record --pid "$PID" --duration "$DURATION" --threads \
		--output "logs/pyspy_${SITUATION}_${STAMP}.svg" > /dev/null 2>&1 &
	SPY=$!
fi

echo "Mesure en cours pendant $DURATION s : ne pas changer de situation..."
TICKS_START=$(cpu_ticks)
TIME_START=$(date +%s)

ELAPSED=0
while [ $ELAPSED -lt "$DURATION" ]
do
	{
		echo
		echo "--- $(date +%H:%M:%S) : threads les plus occupes"
		# The first frame of top counts since the start of the process : the second one
		top -b -H -n 2 -d 1 -p "$PID" | awk '/^top -/ { n++ } n == 2' | sed -n '7,12p'
	} >> "$OUT"
	sleep 4
	ELAPSED=$((ELAPSED + 5))
done

TICKS_END=$(cpu_ticks)
TIME_END=$(date +%s)
HZ=$(getconf CLK_TCK)

{
	echo
	echo "CPU moyen du jeu : $(awk -v t=$((TICKS_END - TICKS_START)) -v s=$((TIME_END - TIME_START)) -v hz="$HZ" 'BEGIN { printf "%.0f %%", 100 * t / hz / s }') (100 % = un coeur entier, $(nproc) coeurs)"
	echo "Charge du systeme : $(cut -d' ' -f1-3 /proc/loadavg)"
	echo "Memoire du jeu : $(awk '/VmRSS/ { print $2 " ko" }' "/proc/$PID/status")"
	echo
	echo "Etat du Pi a la fin :"
	pi_state
} >> "$OUT"

if [ -n "$SPY" ]
then
	wait "$SPY"
	echo "Profil py-spy : logs/pyspy_${SITUATION}_${STAMP}.svg" >> "$OUT"
fi

cat "$OUT"
