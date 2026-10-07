on run argv
    set inputFile to POSIX file (item 1 of argv)
    set outputFile to POSIX file (item 2 of argv)
    with timeout of 90 seconds
        tell application "Numbers"
            set auditDocument to open inputFile
            set ready to false
            repeat with attempt from 1 to 60
                try
                    set auditValue to value of cell "B8" of table 1 of sheet "Check" of auditDocument
                    if class of auditValue is real or class of auditValue is integer then
                        set ready to true
                        exit repeat
                    end if
                end try
                delay 1
            end repeat
            if ready is false then error "Spreadsheet formulas did not finish calculating within 60 seconds"
            export auditDocument to outputFile as Microsoft Excel
            close auditDocument saving no
        end tell
    end timeout
end run
