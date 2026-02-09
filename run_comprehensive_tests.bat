@echo off
echo ================================================================================
echo COMPREHENSIVE LAW EXTRACTION TEST SUITE
echo Single-page processing - 100%% Gemini 2.5 Flash
echo Screenshots saved to: page_screenshots_multimodel/
echo ================================================================================
echo.

echo Test 1/5: Cap. 559 - Academy for Disciplined Forces (Short Act)
python test_law.py "All Malta law PDFs/Academy for Disciplined Forces Act (Cap. 559).pdf" "Cap. 559" "Academy for Disciplined Forces Act" 0 10 > test_cap559_short.txt 2>&1
echo   Completed. Output: test_cap559_short.txt
echo.

echo Test 2/5: S.L. 281.01 - Accountancy Profession Regulations (Subsidiary)
python test_law.py "All Malta law PDFs/Accountancy Profession Regulations (S.L. 281.01).pdf" "S.L. 281.01" "Accountancy Profession Regulations" 0 15 > test_sl281_subsidiary.txt 2>&1
echo   Completed. Output: test_sl281_subsidiary.txt
echo.

echo Test 3/5: Cap. 16 - Civil Code Extract (Complex Structure)
python test_law.py "All Malta law PDFs/Civil Code (Cap. 16).pdf" "Cap. 16" "Civil Code" 0 20 > test_cap16_civil_code.txt 2>&1
echo   Completed. Output: test_cap16_civil_code.txt
echo.

echo Test 4/5: Cap. 9 - Criminal Code Extract (Penal Law)
python test_law.py "All Malta law PDFs/Criminal Code (Cap. 9).pdf" "Cap. 9" "Criminal Code" 0 25 > test_cap9_criminal_code.txt 2>&1
echo   Completed. Output: test_cap9_criminal_code.txt
echo.

echo Test 5/5: Cap. 220 - Malta Armed Forces Act (Many Articles)
python test_law.py "All Malta law PDFs/Malta Armed Forces Act (Cap. 220).pdf" "Cap. 220" "Malta Armed Forces Act" 0 30 > test_cap220_armed_forces.txt 2>&1
echo   Completed. Output: test_cap220_armed_forces.txt
echo.

echo ================================================================================
echo ALL TESTS COMPLETE
echo ================================================================================
echo Check test_*.txt files for results
echo Check page_screenshots_multimodel/ for page screenshots
echo Check article_extraction_*.json for extracted data
echo Check debug_extraction_*.json for detailed debug info
echo ================================================================================
