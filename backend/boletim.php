<?php
/**
 * Gera o boletim em HTML a partir dos dados de um culto.
 * Opcionalmente pode ser convertido para PDF com ferramentas como wkhtmltopdf.
 */

declare(strict_types=1);

if (php_sapi_name() === 'cli-server') {
    $_SERVER['DOCUMENT_ROOT'] = __DIR__;
}

$configPath = __DIR__ . '/config.php';
if (!file_exists($configPath)) {
    http_response_code(500);
    echo "Crie backend/config.php (copie de config.sample.php) antes de usar.";
    exit;
}

$config = require $configPath;
$dsn = sprintf(
    'mysql:host=%s;port=%d;dbname=%s;charset=%s',
    $config['host'],
    $config['port'],
    $config['database'],
    $config['charset']
);
try {
    $pdo = new PDO($dsn, $config['user'], $config['password'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    echo "Falha ao conectar ao banco: " . $e->getMessage();
    exit;
}

$dateIso = $_GET['data'] ?? null;
if (!$dateIso) {
    http_response_code(400);
    echo "Informe ?data=YYYY-MM-DD ou ?data_texto=DOMINGO,...";
    exit;
}

$stmt = $pdo->prepare('SELECT * FROM cultos WHERE data_iso = :iso OR data_texto = :texto LIMIT 1');
$stmt->execute([':iso' => $dateIso, ':texto' => $dateIso]);
$culto = $stmt->fetch();
if (!$culto) {
    http_response_code(404);
    echo "Culto não encontrado para {$dateIso}";
    exit;
}

$templatePath = __DIR__ . '/templates/boletim-template.html';
if (!file_exists($templatePath)) {
    http_response_code(500);
    echo "Template não encontrado: {$templatePath}";
    exit;
}

$template = file_get_contents($templatePath);

$musicFields = [
    ['label' => 'Louvor 1', 'song' => 'musica1', 'singer' => 'cantor1', 'tone' => 'tom1'],
    ['label' => 'Louvor 2', 'song' => 'musica2', 'singer' => 'cantor2', 'tone' => 'tom2'],
    ['label' => 'Louvor 3', 'song' => 'musica3', 'singer' => 'cantor3', 'tone' => 'tom3'],
    ['label' => 'Oferta / Intercessão', 'song' => 'musica_oferta', 'singer' => 'cantor_oferta', 'tone' => 'tom_oferta'],
    ['label' => 'Ceia (Pão)', 'song' => 'musica_pao', 'singer' => 'cantor_pao', 'tone' => 'tom_pao'],
];

$musicList = [];
foreach ($musicFields as $field) {
    if (empty($culto[$field['song']])) {
        continue;
    }
    $parts = [];
    $parts[] = "<strong>{$field['label']}:</strong> " . htmlspecialchars($culto[$field['song']], ENT_QUOTES | ENT_SUBSTITUTE, 'utf-8');
    if (!empty($culto[$field['singer']])) {
        $parts[] = "Cantor: " . htmlspecialchars($culto[$field['singer']], ENT_QUOTES | ENT_SUBSTITUTE, 'utf-8');
    }
    if (!empty($culto[$field['tone']])) {
        $parts[] = "Tom: " . htmlspecialchars($culto[$field['tone']], ENT_QUOTES | ENT_SUBSTITUTE, 'utf-8');
    }
    $musicList[] = '<li>' . implode(' · ', $parts) . '</li>';
}
$musicRendered = implode("\n", $musicList);

function htmlSafe(?string $value, string $fallback = '—'): string
{
    if ($value === null || $value === '') {
        return $fallback;
    }
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'utf-8');
}

$replacements = [
    '{{data_texto}}' => htmlSafe($culto['data_texto']),
    '{{dirigente}}' => htmlSafe($culto['dirigente']),
    '{{pregador}}' => htmlSafe($culto['pregador']),
    '{{preludio}}' => htmlSafe($culto['preludio']),
    '{{cantor_preludio}}' => htmlSafe($culto['cantor_preludio']),
    '{{tom_preludio}}' => htmlSafe($culto['tom_preludio']),
    '{{ref}}' => htmlSafe($culto['ref']),
    '{{texto}}' => nl2br(htmlSafe($culto['texto'], '')),
    '{{musicas}}' => $musicRendered ?: '<li>Sem músicas registradas.</li>',
    '{{oracao}}' => nl2br(htmlSafe($culto['oracao'] ?? null, '')),
    '{{oracao_2}}' => nl2br(htmlSafe($culto['oracao_2'] ?? $culto['oracao2'] ?? '', '')),
    '{{ofertas_ref}}' => htmlSafe($culto['ofertas_ref'] ?? $culto['ofertasref'] ?? null),
    '{{ofertas_texto}}' => nl2br(htmlSafe($culto['ofertas_texto'] ?? $culto['ofertastexto'] ?? null)),
    '{{intercessao}}' => nl2br(htmlSafe($culto['intercessao'] ?? null)),
    '{{musica_pao}}' => htmlSafe($culto['musica_pao'] ?? null),
    '{{cantor_pao}}' => htmlSafe($culto['cantor_pao'] ?? null),
    '{{tom_pao}}' => htmlSafe($culto['tom_pao'] ?? null),
    '{{musica_vinho}}' => htmlSafe($culto['musica_vinho'] ?? null),
    '{{cantor_vinho}}' => htmlSafe($culto['cantor_vinho'] ?? null),
    '{{tom_vinho}}' => htmlSafe($culto['tom_vinho'] ?? null),
    '{{musica_extra}}' => htmlSafe($culto['musica_extra'] ?? null),
    '{{cantor_extra}}' => htmlSafe($culto['cantor_extra'] ?? null),
    '{{tom_extra}}' => htmlSafe($culto['tom_extra'] ?? null),
    '{{musica_final}}' => htmlSafe($culto['musica_final'] ?? null),
    '{{cantor_final}}' => htmlSafe($culto['cantor_final'] ?? null),
    '{{tom_final}}' => htmlSafe($culto['tom_final'] ?? null),
];

$html = strtr($template, $replacements);

header('Content-Type: text/html; charset=utf-8');
echo $html;
