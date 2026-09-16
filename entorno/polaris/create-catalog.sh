#!/bin/sh

set -eu

apk add --no-cache jq >/dev/null

BASE_URL="http://polaris:8181"
CATALOG_NAME="${ICEBERG_CATALOG:-quickstart_catalog}"
BUCKET="${ICEBERG_BUCKET:-tcdm-iceberg}"
REALM="${POLARIS_REALM:-POLARIS}"
CLIENT_ID="${POLARIS_CLIENT_ID:-root}"
CLIENT_SECRET="${POLARIS_CLIENT_SECRET:-s3cr3t}"

echo "Solicitando credenciales OAuth2 a Polaris..."
token_response="$(curl --fail-with-body -sS -X POST \
    "${BASE_URL}/api/catalog/v1/oauth/tokens" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=PRINCIPAL_ROLE:ALL")"
token="$(printf '%s' "$token_response" | jq -r '.access_token')"

if [ -z "$token" ] || [ "$token" = "null" ]; then
    echo "No se pudo obtener el token de Polaris" >&2
    exit 1
fi

catalog_payload=$(cat <<EOF
{
  "catalog": {
    "name": "${CATALOG_NAME}",
    "type": "INTERNAL",
    "readOnly": false,
    "properties": {
      "default-base-location": "s3://${BUCKET}"
    },
    "storageConfigInfo": {
      "storageType": "S3",
      "allowedLocations": ["s3://${BUCKET}"],
      "endpoint": "http://localhost:9000",
      "endpointInternal": "http://rustfs:9000",
      "pathStyleAccess": true,
      "region": "us-east-1"
    }
  }
}
EOF
)

echo "Creando o verificando el catálogo ${CATALOG_NAME}..."
catalog_response_file=/tmp/catalog-response
catalog_status="$(curl -sS -o "$catalog_response_file" -w '%{http_code}' \
    -X POST "${BASE_URL}/api/management/v1/catalogs" \
    -H "Authorization: Bearer ${token}" \
    -H "Polaris-Realm: ${REALM}" \
    -H 'Content-Type: application/json' \
    -d "$catalog_payload")"

case "$catalog_status" in
    2*) echo "Catálogo ${CATALOG_NAME} creado" ;;
    409) echo "Catálogo ${CATALOG_NAME} ya existía" ;;
    *) echo "Error creando el catálogo (HTTP ${catalog_status})" >&2; cat "$catalog_response_file" >&2; exit 1 ;;
esac

namespace_response_file=/tmp/namespace-response
namespace_status="$(curl -sS -o "$namespace_response_file" -w '%{http_code}' \
    -X POST "${BASE_URL}/api/catalog/v1/${CATALOG_NAME}/namespaces" \
    -H "Authorization: Bearer ${token}" \
    -H "Polaris-Realm: ${REALM}" \
    -H 'Content-Type: application/json' \
    -d '{"namespace":["demo"],"properties":{}}')"

case "$namespace_status" in
    2*) echo "Namespace demo creado" ;;
    409) echo "Namespace demo ya existía" ;;
    *) echo "Error creando el namespace (HTTP ${namespace_status})" >&2; cat "$namespace_response_file" >&2; exit 1 ;;
esac

cat <<EOF
Polaris listo:
  catálogo: ${CATALOG_NAME}
  namespace inicial: demo
  REST: ${BASE_URL}/api/catalog/v1
  management: ${BASE_URL}/api/management/v1
EOF

touch /tmp/polaris-setup-done
tail -f /dev/null
