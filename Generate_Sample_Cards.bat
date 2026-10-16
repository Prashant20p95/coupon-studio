@echo off
title Umang Utsav - Batch Sample Generator
cd /d "%~dp0"
echo ===================================================
echo   Generating Sample Event Cards...
echo ===================================================
echo.
python make_cards.py --csv sample_guests.csv -o output_cards/all_sample_cards.pdf
python make_cards.py --csv sample_guests.csv --by-location output_cards/by_location/
echo.
echo ===================================================
echo Done! Check output_cards/ folder.
echo ===================================================
pause
