<?php
/** API mínima para listar/inserir cultos (uso com php+MySQL/phpMyAdmin). */

declare(strict_types=1);

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$configPath = __DIR__ . '/config.php';
if (!file_exists($configPath)) {
    http_response_code(500);
    echo json_encode(['error' => 'Configuração não encontrada. Copie config.sample.php para config.php.']);
    exit;
}

$config = require $configPath;
$dsn = sprintf('mysql:host=%s;port=%d;dbname=%s;charset=%s', $config['host'], $config['port'], $config['database'], $config['charset']);

try {
    $pdo = new PDO($dsn, $config['user'], $config['password'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Não foi possível conectar ao banco: ' . $e->getMessage()]);
    exit;
}

switch ($_SERVER['REQUEST_METHOD']) {
    case 'GET':
        $stmt = $pdo->query('SELECT * FROM cultos ORDER BY data_iso DESC');
        $cultos = $stmt->fetchAll();
        echo json_encode(['cultos' => $cultos]);
        break;
    case 'POST':
        $payload = json_decode(file_get_contents('php://input'), true);
        if (!is_array($payload)) {
            http_response_code(400);
            echo json_encode(['error' => 'JSON inválido']);
            break;
        }
        $fields = [
            'data_texto' => null,
            'data_iso' => null,
            'dirigente' => null,
            'preludio' => null,
            'cantor_preludio' => null,
            'tom_preludio' => null,
            'ref' => null,
            'texto' => null,
            'oracao' => null,
            'oracao_2' => null,
            'ofertas_ref' => null,
            'ofertas_texto' => null,
            'intercessao' => null,
            'musica1' => null,
            'cantor1' => null,
            'tom1' => null,
            'musica2' => null,
            'cantor2' => null,
            'tom2' => null,
            'musica3' => null,
            'cantor3' => null,
            'tom3' => null,
            'musica_oferta' => null,
            'cantor_oferta' => null,
            'tom_oferta' => null,
            'musica_pao' => null,
            'cantor_pao' => null,
            'tom_pao' => null,
            'musica_vinho' => null,
            'cantor_vinho' => null,
            'tom_vinho' => null,
            'musica_extra' => null,
            'cantor_extra' => null,
            'tom_extra' => null,
            'musica_final' => null,
            'cantor_final' => null,
            'tom_final' => null,
            'pregador' => null,
        ];
        foreach ($fields as $key => &$value) {
            if (array_key_exists($key, $payload)) {
                $value = $payload[$key];
            }
        }
        $sql = 'INSERT INTO cultos
            (data_texto, data_iso, dirigente, preludio, cantor_preludio, tom_preludio, ref, texto, oracao, oracao_2, ofertas_ref, ofertas_texto, intercessao, musica1, cantor1, tom1, musica2, cantor2, tom2, musica3, cantor3, tom3, musica_oferta, cantor_oferta, tom_oferta, musica_pao, cantor_pao, tom_pao, musica_vinho, cantor_vinho, tom_vinho, musica_extra, cantor_extra, tom_extra, musica_final, cantor_final, tom_final, pregador)
            VALUES
            (:data_texto, :data_iso, :dirigente, :preludio, :cantor_preludio, :tom_preludio, :ref, :texto, :oracao, :oracao_2, :ofertas_ref, :ofertas_texto, :intercessao, :musica1, :cantor1, :tom1, :musica2, :cantor2, :tom2, :musica3, :cantor3, :tom3, :musica_oferta, :cantor_oferta, :tom_oferta, :musica_pao, :cantor_pao, :tom_pao, :musica_vinho, :cantor_vinho, :tom_vinho, :musica_extra, :cantor_extra, :tom_extra, :musica_final, :cantor_final, :tom_final, :pregador)';
        $stmt = $pdo->prepare($sql);
        try {
            $stmt->execute($fields);
            echo json_encode(['success' => true, 'id' => $pdo->lastInsertId()]);
        } catch (PDOException $e) {
            http_response_code(400);
            echo json_encode(['error' => $e->getMessage()]);
        }
        break;
    default:
        http_response_code(405);
        echo json_encode(['error' => 'Método não permitido']);
        break;
}
