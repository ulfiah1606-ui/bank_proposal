<?php

require 'vendor/autoload.php';

use thiagoalessio\TesseractOCR\TesseractOCR;

// fungsi OCR
function bacaOCR($file) {
    return (new TesseractOCR($file))
        ->executable('C:\Program Files\Tesseract-OCR\tesseract.exe')
        ->lang('ind')
        ->run();
}

// =======================
// UPLOAD FILE
// =======================
$ktpPath = 'uploads/' . $_FILES['ktp']['name'];
$simluhtanPath = 'uploads/' . $_FILES['simluhtan']['name'];

move_uploaded_file($_FILES['ktp']['tmp_name'], $ktpPath);
move_uploaded_file($_FILES['simluhtan']['tmp_name'], $simluhtanPath);

// =======================
// OCR
// =======================
$ktpText = strtolower(bacaOCR($ktpPath));
$simluhtanText = strtolower(bacaOCR($simluhtanPath));

// =======================
// VALIDASI KTP
// =======================
$ktpScore = 0;

if (strpos($ktpText, 'nik') !== false) $ktpScore++;
if (strpos($ktpText, 'nama') !== false) $ktpScore++;
if (strpos($ktpText, 'alamat') !== false) $ktpScore++;

$ktpValid = $ktpScore >= 2;

// =======================
// VALIDASI SIMLUHTAN
// =======================
$simluhtanScore = 0;

if (strpos($simluhtanText, 'simluhtan') !== false) $simluhtanScore++;
if (strpos($simluhtanText, 'kelompok tani') !== false) $simluhtanScore++;
if (strpos($simluhtanText, 'penyuluh') !== false) $simluhtanScore++;

$simluhtanValid = $simluhtanScore >= 1;

// =======================
// HASIL
// =======================
echo "<h2>HASIL VALIDASI</h2>";

echo "KTP: " . ($ktpValid ? "VALID ✅" : "TIDAK VALID ❌") . "<br>";
echo "Simluhtan: " . ($simluhtanValid ? "VALID ✅" : "TIDAK VALID ❌") . "<br>";

echo "<hr><b>Teks KTP:</b><br>$ktpText<br>";
echo "<hr><b>Teks Simluhtan:</b><br>$simluhtanText<br>";