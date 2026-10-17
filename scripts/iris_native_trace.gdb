set pagination off
set confirm off
set print thread-events off
set debuginfod enabled off
break gsetjrn
commands
silent
printf "PHASE_HIT|gsetjrn|"
shell date -u +%H:%M:%S.%N
bt 4
continue
end
break journalset
commands
silent
printf "PHASE_HIT|journalset|"
shell date -u +%H:%M:%S.%N
bt 4
continue
end
break tcommit
commands
silent
printf "PHASE_HIT|tcommit|"
shell date -u +%H:%M:%S.%N
bt 4
continue
end
break journaltran
commands
silent
printf "PHASE_HIT|journaltran|"
shell date -u +%H:%M:%S.%N
bt 5
continue
end
break journaltranlv
commands
silent
printf "PHASE_HIT|journaltranlv|"
shell date -u +%H:%M:%S.%N
bt 4
continue
end
break jrncmtsync
commands
silent
printf "PHASE_HIT|jrncmtsync|"
shell date -u +%H:%M:%S.%N
bt 4
continue
end
continue
