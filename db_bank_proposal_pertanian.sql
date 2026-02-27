-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Feb 27, 2026 at 03:00 PM
-- Server version: 8.0.30
-- PHP Version: 8.1.10

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `db_bank_proposal_pertanian`
--

-- --------------------------------------------------------

--
-- Table structure for table `anggota_kelompok`
--

CREATE TABLE `anggota_kelompok` (
  `id_anggota` int NOT NULL,
  `id_kelompok` int DEFAULT NULL,
  `nama` varchar(100) DEFAULT NULL,
  `nik` varchar(30) DEFAULT NULL,
  `jabatan` varchar(50) DEFAULT NULL,
  `alamat` varchar(200) DEFAULT NULL,
  `luas_lahan` decimal(10,2) DEFAULT NULL,
  `kebutuhan` decimal(10,2) DEFAULT NULL,
  `koordinat` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Triggers `anggota_kelompok`
--
DELIMITER $$
CREATE TRIGGER `hitung_total_luas` AFTER INSERT ON `anggota_kelompok` FOR EACH ROW BEGIN
    UPDATE proposal p
    SET total_luas = (
        SELECT IFNULL(SUM(luas_lahan),0)
        FROM anggota_kelompok
        WHERE id_kelompok = NEW.id_kelompok
    ),
    total_kebutuhan = (
        SELECT IFNULL(SUM(kebutuhan),0)
        FROM anggota_kelompok
        WHERE id_kelompok = NEW.id_kelompok
    )
    WHERE p.id_kelompok = NEW.id_kelompok;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `catatan_penyuluh`
--

CREATE TABLE `catatan_penyuluh` (
  `id_catatan` int NOT NULL,
  `id_proposal` varchar(20) DEFAULT NULL,
  `id_user` int DEFAULT NULL,
  `catatan` text,
  `tanggal` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `hasil_ai`
--

CREATE TABLE `hasil_ai` (
  `id_ai` int NOT NULL,
  `id_proposal` varchar(20) DEFAULT NULL,
  `skor_kelayakan` decimal(5,2) DEFAULT NULL,
  `skor_urgensi` decimal(5,2) DEFAULT NULL,
  `ringkasan` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `hasil_ai`
--

INSERT INTO `hasil_ai` (`id_ai`, `id_proposal`, `skor_kelayakan`, `skor_urgensi`, `ringkasan`, `created_at`) VALUES
(21, '3252c93f-530', 70.00, 78.00, '-', '2026-02-25 15:41:10');

-- --------------------------------------------------------

--
-- Table structure for table `hasil_clustering`
--

CREATE TABLE `hasil_clustering` (
  `id_cluster` int NOT NULL,
  `id_proposal` varchar(20) DEFAULT NULL,
  `cluster` int DEFAULT NULL,
  `kategori_prioritas` varchar(20) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `kelompok_tani`
--

CREATE TABLE `kelompok_tani` (
  `id_kelompok` int NOT NULL,
  `nama_kelompok` varchar(150) DEFAULT NULL,
  `nama_ketua` varchar(100) DEFAULT NULL,
  `nik_ketua` varchar(30) DEFAULT NULL,
  `ttd_ketua` varchar(255) DEFAULT NULL,
  `kecamatan` varchar(100) DEFAULT NULL,
  `kabupaten` varchar(100) DEFAULT 'Gowa',
  `desa` varchar(100) DEFAULT NULL,
  `jumlah_anggota` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `password` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `kelompok_tani`
--

INSERT INTO `kelompok_tani` (`id_kelompok`, `nama_kelompok`, `nama_ketua`, `nik_ketua`, `ttd_ketua`, `kecamatan`, `kabupaten`, `desa`, `jumlah_anggota`, `created_at`, `password`) VALUES
(26, 'uppy', 'ulfi', NULL, NULL, 'Manuju', 'Gowa', 'Tassese', 20, '2026-02-18 13:57:47', '12345'),
(27, 'mela', 'melos', NULL, NULL, 'todpul', 'Gowa', 'panakkukang', 30, '2026-02-18 14:30:25', '12345'),
(28, 'clustering', 'uppy', NULL, NULL, 'makassar', 'Gowa', 'panakkukang', 30, '2026-02-25 13:05:34', '1234567890'),
(29, 'clustering', 'uppy', NULL, NULL, 'panaikang', 'Gowa', 'panakkukang', 20, '2026-02-25 15:30:31', '1314');

-- --------------------------------------------------------

--
-- Table structure for table `penyuluh`
--

CREATE TABLE `penyuluh` (
  `id_penyuluh` int NOT NULL,
  `nama_lengkap` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `nip_penyuluh` varchar(50) DEFAULT NULL,
  `ttd_penyuluh` longtext,
  `username` varchar(50) DEFAULT NULL,
  `password` varchar(100) DEFAULT NULL,
  `kecamatan` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `penyuluh`
--

INSERT INTO `penyuluh` (`id_penyuluh`, `nama_lengkap`, `nip_penyuluh`, `ttd_penyuluh`, `username`, `password`, `kecamatan`) VALUES
(6, 'ulfiah', '198503122014031001', NULL, 'ulpi', 'penyuluh4', 'panaikang');

-- --------------------------------------------------------

--
-- Table structure for table `proposal`
--

CREATE TABLE `proposal` (
  `id_proposal` varchar(20) NOT NULL,
  `id_kelompok` int DEFAULT NULL,
  `tanggal_pengajuan` date DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `nama_ketua` varchar(150) DEFAULT NULL,
  `nip_ketua` varchar(50) DEFAULT NULL,
  `ttd_poktan` longtext,
  `nama_kepala` varchar(150) DEFAULT NULL,
  `nip_kepala` varchar(50) DEFAULT NULL,
  `ttd_kepala` longtext,
  `nama_ppl` varchar(150) DEFAULT NULL,
  `nip_ppl` varchar(50) DEFAULT NULL,
  `ttd_ppl` longtext,
  `tanggal_ttd` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `proposal`
--

INSERT INTO `proposal` (`id_proposal`, `id_kelompok`, `tanggal_pengajuan`, `status`, `nama_ketua`, `nip_ketua`, `ttd_poktan`, `nama_kepala`, `nip_kepala`, `ttd_kepala`, `nama_ppl`, `nip_ppl`, `ttd_ppl`, `tanggal_ttd`) VALUES
('3252c93f-530', 29, '2026-02-25', 'selesai', 'paje', '7301010101010001', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAACWCAYAAADwkd5lAAANmklEQVR4AeydW+g1VRnG/5akWRZoRJaKp8zKiz7rEyujc4HZ4UYjykIQLySECqKICko6XHjRhRcGSXkRZUQZSUUHKkWt6HTTwTIrTT9LNMmiE+rz4Foi2/9h7z1rz7zvmp+sZ6/Ze8+s9a7f+9fHmTVr9mO2+AcCEIAABCCwBgEMZA1oHAIBCEAAAltbGAh/BRCYigD9QiA5AQwkeQIJHwIQgMBUBDCQqcjTLwQgAIHkBBIbSHLyhA8BCEAgOQEMJHkCCR8CEIDAVAQwkKnI0y8EEhMgdAiYAAZiCggCEIAABFYmgIGsjIwDIAABCEDABDAQUxhb9AcBCECgAwIYSAdJZAgQgAAEpiCAgUxBnT4hAIGpCNBvQwIYSEOYNAUBCEBgTgQwkDllm7FCAAIQaEgAA2kIcw5NMUYIQAAClQAGUklQQwACEIDASgQwkJVwsTMEIACBqQjE6xcDiZcTIoIABCCQggAGkiJNBAkBCEAgHgEMJF5OiGgzBGgVAhBoTAADaQyU5iAAAQjMhQAGMpdMDxvncTr8CulK6d1Sra/X9gclv/+iaqt+7+2f6LOvSldJX5P2SRQIQKATAksbSCfjZRjLEzhYu35LukG6RTpfOk+6VKr1C7X9Ecnvz1Vt1e+9/QJ99kbpHOn10g+kUyQKBCDQAQEMpIMkNh6CjcNnDH9Qu6+RzpBcDujl99I3pF9L35XukW6UbpJulf4o+Xu//4u275PulG6T/iUdLvl7VRQIQCA7AQwkewbbxm/zuFlN+ozhGNX/lz4rHSQdJT1TOkt6jvQq6QjJZyHPUn2sdLzk7/3+aG3bMJ6m2m3ZcLS59VS9fEHicpYgLFfYCwIxCWAgMfOyyag+p8Y9P7Eoz13YPGwE92sfn0G8U7UvXakaXD6sFv4hHSa9Wfq0RIEABBITwEASJ2/F0H12cZeOebvk+YlFee6imsfF2sdnEJerblV+roZOl/4k+XKW50derG0KBCCQlMAcDCRpapqHfYdaPFJy+a9ePGdR5bmLb+szn4FcpPoyaRPlN2rUd3Rdp9rlGr2cJlEgAIGEBDCQhElbI2RPij9Fxz0geTLcZxg+26jy3IUnzE/S9y3POtTctuVCfXqv9GTpWgkTEQQKBLIRwECyZWy9eB9bDrtdtSfDxzAJdbVj8WWsV+hbX8rynMgPtf18idIbAcbTNQEMpOv0Pjw4n2n4jf+P33UE/UxBvET6p/QEyXd7qaJAAAJZCGAgWTI1LE7fUeUWfBeU6yiyibxUwdhETlV9pkSBAASSEMBAQieqWXC+ROTGfuGXYPqp4vEEvqqtj/oFQQACOQhgIDnyNDTK55UGTix1tOpdCujv0sukr0snSxQIQCA4AQwkeIIahXdIaccT1mUzVOXbiD2x7qBep5evSBQITEqAzvcmgIHszaiHPerk+d8CD8YLG+scTTWTwOESGgQggIHM42/giWWYnrQum+EqP4DRj353YFEvtTk2BAEIFAIYSAHRceWV3/WRIReMNs71OqqX2nxb73otcBQEIDAaAQxkNNSTdfSh0rMXEZbNsNUJJbJ6ya28pYIABCISwEAiZqVtTP69DrdYa29HVV2v4nUhUWMkLghEJzBafBjIaKgn66guznv2ZBEs3/F/yq5+2GPZpIIABKISwECiZqZdXHXxoG+VbdfqZlvi73KzfGkdAk0I8C9qE4yhG6mLCD2ZHjpQBRdiDkRxUCAAgSUIYCBLQEq+S6YzEOZAkv+xEf68CGAg/ec70xkIcyD9/z0ywo4ItDeQjuB0MpRMZyAHFeYHl5oKAhAITAADCZycRqFlOgN5ZRnzk0pNBQEIBCaAgQROTqPQ6hmIHxXSqMmNNPMltXqE5J/dnfoXExVGykLQEBiVAAYyKu5JOruv9HpvqSNWvmT1ohKYV8y/p2xTQQACgQlgIIGT0yi0upBwf6P2WjXzODX0ecmPbvcaladr+37p4xIFAhBIQAADeUSSOt2Mdgnr8eJ8jXS39BbpTdIzJJvHxaovkygQgEACAhhIgiQNDDHSJSxfqvqdxnOW5Cfu3qHaaz+si7SNeQgCBQJZCGAgWTK1fpyRLmH9WMOoZxvv07YvWx2t2mLiXCDmWxh5RgIYSMasrRbzVJew6hzHBxTuhdKPpH2SH5ToS1Wf1DYFAhBITAADSZy8JUMf+xKWjcNnF3cpPs9xXKLaZxenq7Z5vFw1l6oEgQKB7AQwkOwZfCj+3V7HuoTlOY2rFYjnNXwn1eHa9tyGJ8x9t9XNeu8zj+tVUyAAgQ4IYCAdJHGPIdRLWL5Vdo9d1/q6GsdfdfQbJC8G/J7qsyXPbbh+q7ZPknwmoooCAQj0QAAD6SGLu4+hPsrkxN13W/nbReM4TC0ckDzn4UeS+MxDbykQ6JzAjIeHgfSf/EPKED03UTYHVXUdx51qxWccjzSOo/TZxyQKBCAwAwIYSP9J9t1PHuUv/dJA16mNuo6jnnFgHIJCgcDcCGAg/We83oXlM4Yho/UvGt6gBk6TfDeV77RqYBxqjQIBCKQkgIGkTNtaQR+6wlFXaN8rpW9KXq/hJ+Teou0zpH9LvhXXn2uTAgEIzJUABtJ/5le5jde34doszheW86TXSu+VXG7Ti03kbaq5FVcQKBDITmBo/BjIUILxj6+38e71eyCXaiieFFe15cteXsPxW735jHS8dIx0gvRliQIBCEBgCwPp/4/AZuBRbvd7IH644VX68v3SuZKLf4/DiwC9huMUfXCBtKk1JGqaAgEIZCWAgWTN3PJx73YJy2cl56gp33prw/Aj1b2tjyh7EmAHCMycAAbS/x/A4iWsetbhOQ1fmrJpfEcY/KgRHqkuEBQIQGA5AhjIcpwy71UvYdXbeOtZhx+r7nH9WS+vlnjUiCBQIACB5QlMaCDLB8meTQj4Nl4/IbeeddyqVj238QnVFAhAAAIrE8BAVkaW7oA6B+K5jiNL9D7rOFbbNhMecCgQFAhAYHUCGMjqzLIdUedA/lcC95wHZx0Fxlwrxg2BFgQwkBYUY7dRn8Z7t8K8R/J6D846BIICAQgMI4CBDOOX4eh6BuKHKfq3OurK8gyxEyMEIBCYAAayTnJyHbN4F1au6IkWAhAISwADCZua5oH5LqzmjdIgBCAwXwIYSP+5r3dh7e9/qIxwBgQYYiACGEigZGwolDoH4gWEG+qCZiEAgTkSwED6zzpzIP3nmBFCYBICGMgk2KfrlJ4hAAEItCKAgbQiGb8dP6I9fpRECAEIpCGAgaRJ1dqBnlyOrHV5SwUBCIxLoL/eMJD+cro4omvLB+S6gKCCAATaEOA/Km04Rm7FK9Ad3z6/IAhAAAKtCGAgrUjGbcePbLcc4XF+SSrChgAEghHAQIIlZEPhYCAbAkuzEJgzAQxkHtmvBnLqPIbLKCEAgaYEdmgMA9kBTGcfP1DG845SU0EAAhAYTAADGYwwRQM3ligPlJoKAhCAwGACGMhghKkauD1VtN0Ey0Ag0CcBDKTPvO40Klaj70SGzyEAgZUJYCArI0t5QF2FXuuUgyBoCEAgFoEMBhKLWM5oWI2eM29EDYHQBDCQ0OlpFtzVpSWvRmcxYYFBBQEIDCOAgQzjl+nouhYkU8zEOjUB+ofALgQwkF3gdPbV98t4zi41FQQgAIFBBDCQQfhSHcxiwlTpIlgIxCeAgWw0R6EaZzFhqHQQDATyE8BA8udw1RGwmHBVYuwPAQhsSwAD2RZL1x8e2vXoGBwECgGqzRPAQDbPOEoPZ5ZA9peaCgIQgMAgAhjIIHypDr5E0f5K+pREgQAEIDCYAAYyGGGaBm5SpM+VLpf2LuwBAQhAYA8CGMgegPgaAhCAAAS2J4CBbM+FTyEAAQhMRSBNvxhImlQRKAQgAIFYBDCQWPkgGghAAAJpCGAgaVJFoMsSYD8IQGAcAhjIOJzpBQIQgEB3BDCQ7lLKgCAAAQiMQ+DRBjJOv/QCAQhAAALJCWAgyRNI+BCAAASmIoCBTEWefiHwaAJ8AoFUBDCQVOkiWAhAAAJxCGAgcXJBJBCAAARSEejKQFKRJ1gIQAACyQlgIMkTSPgQgAAEpiKAgUxFnn4h0BUBBjNHAhjIHLPOmCEAAQg0IICBNIBIExCAAATmSAADiZF1ooAABCCQjgAGki5lBAwBCEAgBgEMJEYeiAICEJiKAP2uTQADWRsdB0IAAhCYNwEMZN75Z/QQgAAE1iaAgayNjgMfIsArBCAwVwIYyFwzz7ghAAEIDCSAgQwEyOEQgAAEpiIwdb8YyNQZoH8IQAACSQlgIEkTR9gQgAAEpiaAgUydAfqfjgA9QwACgwhgIIPwcTAEIACB+RLAQOabe0YOAQhAYBCBAQYyqF8OhgAEIACB5AQwkOQJJHwIQAACUxHAQKYiT78QGECAQyEQgQAGEiELxAABCEAgIQEMJGHSCBkCEIBABALzNJAI5IkBAhCAQHICGEjyBBI+BCAAgakIYCBTkadfCMyTAKPuiAAG0lEyGQoEIACBMQlgIGPSpi8IQAACHRHAQJIlk3AhAAEIRCGAgUTJBHFAAAIQSEYAA0mWMMKFAASmIkC/iwQwkEUivIcABCAAgaUIYCBLYWInCEAAAhBYJICBLBLh/aYI0C4EINAZAQyks4QyHAhAAAJjEXgQAAD//6dM2qsAAAAGSURBVAMAkg0ePFLdkkoAAAAASUVORK5CYII=', NULL, NULL, NULL, 'ulfiah', '198503122014031001', 'data:image/png;base64,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', '2026-02-25 23:39:06');

-- --------------------------------------------------------

--
-- Table structure for table `proposal_dokumen`
--

CREATE TABLE `proposal_dokumen` (
  `id` int NOT NULL,
  `id_proposal` varchar(20) NOT NULL,
  `foto_ktp` varchar(255) DEFAULT NULL,
  `ss_simluhtan` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `proposal_dokumen`
--

INSERT INTO `proposal_dokumen` (`id`, `id_proposal`, `foto_ktp`, `ss_simluhtan`) VALUES
(11, '3252c93f-530', 'static/uploads\\3252c93f-530_ktp.jpg', 'static/uploads\\3252c93f-530_simluhtan.jpg');

-- --------------------------------------------------------

--
-- Table structure for table `proposal_metrik`
--

CREATE TABLE `proposal_metrik` (
  `id_metrik` int NOT NULL,
  `id_proposal` varchar(20) NOT NULL,
  `luas_lahan` int DEFAULT '0',
  `jumlah_bantuan` int DEFAULT '0',
  `pagu_anggaran` int DEFAULT '0',
  `jumlah_bantuan_sebelumnya` int DEFAULT '0',
  `latitude` decimal(10,6) DEFAULT NULL,
  `longitude` decimal(10,6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `proposal_narasi`
--

CREATE TABLE `proposal_narasi` (
  `id_narasi` int NOT NULL,
  `id_proposal` varchar(20) NOT NULL,
  `latar_belakang` text NOT NULL,
  `maksud` text,
  `tujuan` text NOT NULL,
  `kebutuhan` text NOT NULL,
  `data_kelompok` text,
  `lokasi` text,
  `penutup` text,
  `permohonan_bantuan` text,
  `nomor_surat` varchar(100) DEFAULT NULL,
  `tanggal_surat` date DEFAULT NULL,
  `lampiran` varchar(100) DEFAULT NULL,
  `perihal` varchar(200) DEFAULT NULL,
  `tujuan_surat` varchar(200) DEFAULT NULL,
  `lokasi_tujuan` varchar(200) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `proposal_narasi`
--

INSERT INTO `proposal_narasi` (`id_narasi`, `id_proposal`, `latar_belakang`, `maksud`, `tujuan`, `kebutuhan`, `data_kelompok`, `lokasi`, `penutup`, `permohonan_bantuan`, `nomor_surat`, `tanggal_surat`, `lampiran`, `perihal`, `tujuan_surat`, `lokasi_tujuan`) VALUES
(11, '3252c93f-530', 'Pertanian adalah salah satu jenis usaha yang mempunyai masa depan yang baik dan menjanjikan bagi peningkatan ekonomi keluarga. Disamping itu, usaha tersebut merupakan usaha yang hasilnya sangat dibutuhkan oleh masyarakat untuk peningkatan gizi serta perkembangan kawasan pertanian yang ada. Disamping itu juga, bantuan berupa Pupuk Organik Cair (POC) dapat memberikan peningkatan produksi pertanian kepada masyarakat terutama bagi kami Kelompok Tani Batu Karopa di Desa Tassese Kecamatan Manuju Kabupaten Gowa. Melihat kondisi ini, maka kami dari kelompok tani “Batu Karopa” memohon kiranya, kami dapat diberikan bantuan dalam hal ini pengadaan Pupuk Organik Cair dalam rangka membantu bersama-sama melaksanakan dan mengembangkan kawasan pertanian di wilayah Kabupaten Gowa khususnya tanaman pangan.', 'Dengan adanya bantuan ini Kelompok Tani Batu Karopa yang kami kelola semakin berkembang dan membawa dampak perubahan peningkatan kesejahteraan keluarga petani secara signifikan.', 'Bantuan ini bertujuan untuk:\r\n\r\nDapat meningkatkan kualitas hidup bagi kelompok tani yang ada dalam KELOMPOK TANI BATU KAROPA.\r\n\r\nMeningkatkan kepedulian para anggota kelompok tani dalam menangani permasalahan sosial yang ada dengan peningkatan kesejahteraan para anggotanya.\r\n\r\nMeningkatkan produksi pertanian terutama tanaman padi yang ada di wilayah Kab. Gowa khususnya Desa Tassese Kecamatan Manuju Kabupaten Gowa.', 'benih padi', '[{\"nama\":\"paje\",\"nik\":\"7301010101010001\",\"jabatan\":\"ketua\",\"alamat\":\"urip\",\"luas\":\"2.00\",\"kebutuhan\":\"50.00\",\"koordinat\":\"-5.329845, 119.708214\"},{\"nama\":\"nisa\",\"nik\":\"7301010101010002\",\"jabatan\":\"sekertaris\",\"alamat\":\"urip\",\"luas\":\"0.50\",\"kebutuhan\":\"12.50\",\"koordinat\":\"-5.331276, 119.710532\"},{\"nama\":\"nurul\",\"nik\":\"7301010101010003\",\"jabatan\":\"bendahara\",\"alamat\":\"sunu\",\"luas\":\"0.50\",\"kebutuhan\":\"12.50\",\"koordinat\":\"-5.333018, 119.712145\"},{\"nama\":\"ucup\",\"nik\":\"7301010101010004\",\"jabatan\":\"anggota\",\"alamat\":\"maccini\",\"luas\":\"1.00\",\"kebutuhan\":\"12.50\",\"koordinat\":\"-5.335402, 119.706978\"},{\"nama\":\"rama\",\"nik\":\"7301010101010005\",\"jabatan\":\"anggota\",\"alamat\":\"vetran\",\"luas\":\"0.20\",\"kebutuhan\":\"5.00\",\"koordinat\":\"-5.338774, 119.711320\"}]', 'KELOMPOK TANI BATU KAROPA terdiri dari gabungan beberapa orang petani yang ada di Desa Tassese Kecamatan Manuju yang terdiri dari 30 orang anggota dengan luas lahan terlampir di CPCL.', 'Demikian proposal ini kami buat, semoga hal ini dapat menjadi bahan pertimbangan Ibu Bupati Kabupaten Gowa dan semoga semua pihak bisa memaklumi dan bersedia membantu kami dan segala kelengkapan Kelompok Tani kami (TERLAMPIR). Atas bantuannya kami ucapkan banyak terima kasih', 'Dengan hormat,\r\n\r\nDalam rangka swasembada pangan dan pengembangan tanaman pangan khususnya padi ang merupakan salah satu program pemerintah dibidang pertanian, maka kami dari Kelompok Tam \"Bilampang\" Desa Tanah karaeng Kecamatan Manuju memohon kepada Ibu Bupati Gowa antu membantu dalam hal pengadaan benih pad\r\n\r\nSebagai bahan pertimbangan Ibu Bupati Gowa, kami lampirkan daftar Calon Petani Calon Lahan (CPCL) Kelompok Tani \"Bilampang\" Desa Tanah karaeng kecamatan manuju\r\n\r\nDemikian permohonan kami, atas perhatian dan kebijaksanan Ibu Bupati Gowa diucapkan bamyak terima kasih,', '0987654321', '2026-02-25', '1 Berkas', 'Permohonan Bantuan', 'Ibu Bupati Kabupaten Gowa', 'Sungguminasa');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id_user` int NOT NULL,
  `nama` varchar(100) DEFAULT NULL,
  `username` varchar(50) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `role` enum('admin','penyuluh') DEFAULT NULL,
  `wilayah_binaan` varchar(100) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id_user`, `nama`, `username`, `password`, `role`, `wilayah_binaan`, `created_at`) VALUES
(2, NULL, 'admin', 'admin', 'admin', NULL, '2026-02-04 06:56:58');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `anggota_kelompok`
--
ALTER TABLE `anggota_kelompok`
  ADD PRIMARY KEY (`id_anggota`),
  ADD KEY `id_kelompok` (`id_kelompok`);

--
-- Indexes for table `catatan_penyuluh`
--
ALTER TABLE `catatan_penyuluh`
  ADD PRIMARY KEY (`id_catatan`),
  ADD KEY `id_proposal` (`id_proposal`),
  ADD KEY `id_user` (`id_user`);

--
-- Indexes for table `hasil_ai`
--
ALTER TABLE `hasil_ai`
  ADD PRIMARY KEY (`id_ai`),
  ADD KEY `id_proposal` (`id_proposal`);

--
-- Indexes for table `hasil_clustering`
--
ALTER TABLE `hasil_clustering`
  ADD PRIMARY KEY (`id_cluster`),
  ADD UNIQUE KEY `id_proposal` (`id_proposal`);

--
-- Indexes for table `kelompok_tani`
--
ALTER TABLE `kelompok_tani`
  ADD PRIMARY KEY (`id_kelompok`);

--
-- Indexes for table `penyuluh`
--
ALTER TABLE `penyuluh`
  ADD PRIMARY KEY (`id_penyuluh`);

--
-- Indexes for table `proposal`
--
ALTER TABLE `proposal`
  ADD PRIMARY KEY (`id_proposal`),
  ADD KEY `id_kelompok` (`id_kelompok`);

--
-- Indexes for table `proposal_dokumen`
--
ALTER TABLE `proposal_dokumen`
  ADD PRIMARY KEY (`id`),
  ADD KEY `id_proposal` (`id_proposal`);

--
-- Indexes for table `proposal_metrik`
--
ALTER TABLE `proposal_metrik`
  ADD PRIMARY KEY (`id_metrik`),
  ADD KEY `id_proposal` (`id_proposal`);

--
-- Indexes for table `proposal_narasi`
--
ALTER TABLE `proposal_narasi`
  ADD PRIMARY KEY (`id_narasi`),
  ADD KEY `id_proposal` (`id_proposal`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id_user`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `anggota_kelompok`
--
ALTER TABLE `anggota_kelompok`
  MODIFY `id_anggota` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `catatan_penyuluh`
--
ALTER TABLE `catatan_penyuluh`
  MODIFY `id_catatan` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `hasil_ai`
--
ALTER TABLE `hasil_ai`
  MODIFY `id_ai` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=22;

--
-- AUTO_INCREMENT for table `hasil_clustering`
--
ALTER TABLE `hasil_clustering`
  MODIFY `id_cluster` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=179;

--
-- AUTO_INCREMENT for table `kelompok_tani`
--
ALTER TABLE `kelompok_tani`
  MODIFY `id_kelompok` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=30;

--
-- AUTO_INCREMENT for table `penyuluh`
--
ALTER TABLE `penyuluh`
  MODIFY `id_penyuluh` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `proposal_dokumen`
--
ALTER TABLE `proposal_dokumen`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT for table `proposal_metrik`
--
ALTER TABLE `proposal_metrik`
  MODIFY `id_metrik` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `proposal_narasi`
--
ALTER TABLE `proposal_narasi`
  MODIFY `id_narasi` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id_user` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `anggota_kelompok`
--
ALTER TABLE `anggota_kelompok`
  ADD CONSTRAINT `anggota_kelompok_ibfk_1` FOREIGN KEY (`id_kelompok`) REFERENCES `kelompok_tani` (`id_kelompok`) ON DELETE CASCADE;

--
-- Constraints for table `catatan_penyuluh`
--
ALTER TABLE `catatan_penyuluh`
  ADD CONSTRAINT `catatan_penyuluh_ibfk_1` FOREIGN KEY (`id_proposal`) REFERENCES `proposal` (`id_proposal`),
  ADD CONSTRAINT `catatan_penyuluh_ibfk_2` FOREIGN KEY (`id_user`) REFERENCES `users` (`id_user`);

--
-- Constraints for table `hasil_ai`
--
ALTER TABLE `hasil_ai`
  ADD CONSTRAINT `hasil_ai_ibfk_1` FOREIGN KEY (`id_proposal`) REFERENCES `proposal` (`id_proposal`);

--
-- Constraints for table `hasil_clustering`
--
ALTER TABLE `hasil_clustering`
  ADD CONSTRAINT `hasil_clustering_ibfk_1` FOREIGN KEY (`id_proposal`) REFERENCES `proposal` (`id_proposal`);

--
-- Constraints for table `proposal`
--
ALTER TABLE `proposal`
  ADD CONSTRAINT `proposal_ibfk_1` FOREIGN KEY (`id_kelompok`) REFERENCES `kelompok_tani` (`id_kelompok`);

--
-- Constraints for table `proposal_dokumen`
--
ALTER TABLE `proposal_dokumen`
  ADD CONSTRAINT `proposal_dokumen_ibfk_1` FOREIGN KEY (`id_proposal`) REFERENCES `proposal` (`id_proposal`) ON DELETE CASCADE;

--
-- Constraints for table `proposal_metrik`
--
ALTER TABLE `proposal_metrik`
  ADD CONSTRAINT `proposal_metrik_ibfk_1` FOREIGN KEY (`id_proposal`) REFERENCES `proposal` (`id_proposal`) ON DELETE CASCADE;

--
-- Constraints for table `proposal_narasi`
--
ALTER TABLE `proposal_narasi`
  ADD CONSTRAINT `proposal_narasi_ibfk_1` FOREIGN KEY (`id_proposal`) REFERENCES `proposal` (`id_proposal`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
