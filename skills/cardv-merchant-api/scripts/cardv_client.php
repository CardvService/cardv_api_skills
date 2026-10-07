<?php
// CardV Merchant API client (PHP 7.4+, ext-curl).
// Signs every call with X-Key-Id + X-Timestamp + X-Nonce + X-Signature.
// Docs: https://cardv.net/developers/authentication/
//
// Usage:
//   CARDV_KEY_ID=ck_test_... CARDV_SIGNING_SECRET=cs_test_... \
//   CARDV_BASE_URL=https://sandbox.cardv.net php cardv_client.php

function cardv_sign(string $secret, string $method, string $path, string $body, string $ts, string $nonce): string
{
    $text = implode("\n", [strtoupper($method), $path, $ts, $nonce, hash('sha256', $body)]);
    return hash_hmac('sha256', $text, $secret); // lowercase hex
}

function cardv_request(string $baseUrl, string $keyId, string $secret, string $method, string $path, ?array $payload = null): array
{
    // Serialize once; the signed bytes must be the sent bytes. Keep the query string inside $path.
    $body = $payload === null ? '' : json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    $ts = (string) time();
    $nonce = bin2hex(random_bytes(16));
    $headers = [
        'X-Key-Id: ' . $keyId,
        'X-Timestamp: ' . $ts,
        'X-Nonce: ' . $nonce,
        'X-Signature: ' . cardv_sign($secret, $method, $path, $body, $ts, $nonce),
        // Replace with your app name and version; a clear User-Agent avoids edge blocks (error code 1010).
        'User-Agent: CardV-Sample-Client/1.0 (php)',
    ];
    $ch = curl_init(rtrim($baseUrl, '/') . $path);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    if (strtoupper($method) === 'POST') {
        $headers[] = 'Content-Type: application/json';
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
    }
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    $response = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return ['status' => $status, 'body' => json_decode((string) $response, true)];
}

// Checks the signing code against the published test vectors (fake secret).
function cardv_self_test(): void
{
    $secret = 'cs_test_TEST_ONLY_not_a_real_secret_0123456789abcdef';
    $ts = '1790000000';
    $nonce = '0123456789abcdef0123456789abcdef';
    $body = '{"external_order_id":"TEST-0001","items":[{"sku_id":"S000001","quantity":1,"expected_unit_price":"9.25"}]}';
    if (cardv_sign($secret, 'GET', '/api/v1/skus?limit=50', '', $ts, $nonce) !== '58f0362c355a6624fff9f0b84d47591c570263908832294375b7bf27731628e5') {
        throw new RuntimeException('GET test vector failed');
    }
    if (cardv_sign($secret, 'POST', '/api/v1/orders', $body, $ts, $nonce) !== 'e6e45d09ed271d8d721701b560d56a6f5104fd8a52aaad5380166f432bba6e89') {
        throw new RuntimeException('POST test vector failed');
    }
    echo "self-test passed\n";
}

if (PHP_SAPI === 'cli' && realpath($argv[0] ?? '') === __FILE__) {
    cardv_self_test();
    $keyId = getenv('CARDV_KEY_ID');
    $secret = getenv('CARDV_SIGNING_SECRET');
    if ($keyId && $secret) {
        $base = getenv('CARDV_BASE_URL') ?: 'https://sandbox.cardv.net';
        var_dump(cardv_request($base, $keyId, $secret, 'GET', '/api/v1/balance'));
    }
}
