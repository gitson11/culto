-- Schema mínimo para armazenar cultos no MySQL (útil com phpMyAdmin)
DROP TABLE IF EXISTS `cultos`;
CREATE TABLE `cultos` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `data_texto` VARCHAR(64) NOT NULL,
  `data_iso` DATE NULL,
  `dirigente` VARCHAR(128),
  `preludio` VARCHAR(255),
  `cantor_preludio` VARCHAR(128),
  `tom_preludio` VARCHAR(16),
  `ref` TEXT,
  `texto` TEXT,
  `oracao` VARCHAR(128),
  `oracao_2` VARCHAR(128),
  `ofertas_ref` VARCHAR(255),
  `ofertas_texto` TEXT,
  `intercessao` VARCHAR(128),
  `musica1` VARCHAR(255),
  `cantor1` VARCHAR(128),
  `tom1` VARCHAR(16),
  `musica2` VARCHAR(255),
  `cantor2` VARCHAR(128),
  `tom2` VARCHAR(16),
  `musica3` VARCHAR(255),
  `cantor3` VARCHAR(128),
  `tom3` VARCHAR(16),
  `musica_oferta` VARCHAR(255),
  `cantor_oferta` VARCHAR(128),
  `tom_oferta` VARCHAR(16),
  `musica_pao` VARCHAR(255),
  `cantor_pao` VARCHAR(128),
  `tom_pao` VARCHAR(16),
  `musica_vinho` VARCHAR(255),
  `cantor_vinho` VARCHAR(128),
  `tom_vinho` VARCHAR(16),
  `musica_extra` VARCHAR(255),
  `cantor_extra` VARCHAR(128),
  `tom_extra` VARCHAR(16),
  `musica_final` VARCHAR(255),
  `cantor_final` VARCHAR(128),
  `tom_final` VARCHAR(16),
  `pregador` VARCHAR(128),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_data` (`data_texto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Exemplos de inserção (adicione mais linhas conforme necessário)
INSERT INTO `cultos` (
  `data_texto`, `data_iso`, `dirigente`, `preludio`, `cantor_preludio`, `tom_preludio`,
  `ref`, `texto`, `oracao`, `oracao_2`, `ofertas_ref`, `ofertas_texto`, `intercessao`,
  `musica1`, `cantor1`, `tom1`
)
VALUES (
  'DOMINGO, 10 DE OUTUBRO DE 2021', '2021-10-10', 'RUBEM', 'Eu Quero é Deus', 'Comunidade de Nilópolis', 'G',
  'JOÃO 3.16', 'PORQUE DEUS AMOU...', 'NÁJILA', NULL, 'MALAQUIAS 3:10', 'TRAZEI TODOS OS DÍZIMOS...', 'RUBEM',
  'DEUS É AMOR', 'ALINE BARROS', 'G'
);
