@echo off
cd /d "e:\Python Projects\RankMyApps Automation"
git -c core.editor=true rebase --continue
git push -u origin master
