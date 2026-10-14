DIR="$(dirname "$(readlink -f "$0")")"
#!/bin/sh

cat $DIR/Backup.sh | tr -d '\r' > $DIR/BackupNew.sh

rm $DIR/Backup.sh

mv $DIR/BackupNew.sh $DIR/Backup.sh

chmod +x $DIR/Backup.sh

cat $DIR/Intro.sh | tr -d '\r' > $DIR/IntroNew.sh

rm $DIR/Intro.sh

mv $DIR/IntroNew.sh $DIR/Intro.sh

chmod +x $DIR/Intro.sh
