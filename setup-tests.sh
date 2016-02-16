#!/bin/bash
set -e -x

wait_for_line () {
    while read line
    do
        echo "$line" | grep -q "$1" && break
    done < "$2"
    # Read the fifo for ever otherwise process would block
    cat "$2" &
}

clean_exit () {
    local error_code="$?"
    kill $(jobs -p)
    rm -rf "$@"
    return $error_code
}

AODH_DATA=`mktemp -d /tmp/aodh-data-XXXXX`
GNOCCHI_DATA=`mktemp -d /tmp/gnocchi-data-XXXXX`
MYSQL_DATA=`mktemp -d /tmp/aodh-mysql-XXXXX`
trap "clean_exit \"$AODH_DATA\" \"$GNOCCHI_DATA\" \"$MYSQL_DATA\"" EXIT

mysqld --initialize-insecure --datadir=${MYSQL_DATA} || true
mkfifo ${MYSQL_DATA}/out
PATH=$PATH:/usr/libexec
mysqld --no-defaults --datadir=${MYSQL_DATA} --pid-file=${MYSQL_DATA}/mysql.pid --socket=${MYSQL_DATA}/mysql.socket --skip-networking --skip-grant-tables &> ${MYSQL_DATA}/out &
# Wait for MySQL to start listening to connections
wait_for_line "mysqld: ready for connections." ${MYSQL_DATA}/out
export AODH_TEST_STORAGE_URL="mysql+pymysql://root@localhost/test?unix_socket=${MYSQL_DATA}/mysql.socket&charset=utf8"
export GNOCCHI_TEST_INDEXER_URL="mysql+pymysql://root@localhost/gnocchi?unix_socket=${MYSQL_DATA}/mysql.socket&charset=utf8"
mysql --no-defaults -S ${MYSQL_DATA}/mysql.socket -e 'CREATE DATABASE test; CREATE DATABASE gnocchi;'



# NOTE(sileht): FIXME: we must use the upstream policy and paste 
# configuration and not a copy, but aodh doesn't yet install
# etc files in virtualenv
cat << EOF > ${AODH_DATA}/policy.json
{
    "context_is_admin": "role:admin",
    "segregation": "rule:context_is_admin",
    "admin_or_owner": "rule:context_is_admin or project_id:%(project_id)s",
    "default": "rule:admin_or_owner",

    "telemetry:get_alarm": "rule:admin_or_owner",
    "telemetry:get_alarms": "rule:admin_or_owner",
    "telemetry:query_alarm": "rule:admin_or_owner",

    "telemetry:create_alarm": "",
    "telemetry:change_alarm": "rule:admin_or_owner",
    "telemetry:delete_alarm": "rule:admin_or_owner",

    "telemetry:get_alarm_state": "rule:admin_or_owner",
    "telemetry:change_alarm_state": "rule:admin_or_owner",

    "telemetry:alarm_history": "rule:admin_or_owner",
    "telemetry:query_alarm_history": "rule:admin_or_owner"
}
EOF
cat << EOF > ${AODH_DATA}/api-paste.ini
[pipeline:main]
# NOTE(sileht): disable authtoken
# pipeline = request_id authtoken api-server
pipeline = request_id api-server

[app:api-server]
paste.app_factory = aodh.api.app:app_factory

[filter:authtoken]
paste.filter_factory = keystonemiddleware.auth_token:filter_factory
oslo_config_project = aodh

[filter:request_id]
paste.filter_factory = oslo_middleware:RequestId.factory
EOF

mkfifo ${AODH_DATA}/out
cat > ${AODH_DATA}/aodh.conf <<EOF
[api]
paste_config = ${AODH_DATA}/api-paste.ini
# paste_config = ${VIRTUAL_ENV}/etc/aodh/api-paste.ini
[oslo_policy]
policy_file = ${AODH_DATA}/policy.json
# policy_file = ${VIRTUAL_ENV}/etc/aodh/policy.json
[database]
connection = $AODH_TEST_STORAGE_URL
[service_credentials]
auth_type = gnocchi-noauth
user_id = e0f4a978-694f-4ad3-b93d-8959374ab091
project_id = e0f4a978-694f-4ad3-b93d-8959374ab091
roles = admin
endpoint = http://localhost:8041/
EOF

aodh-dbsync --config-file ${AODH_DATA}/aodh.conf
aodh-api --config-file ${AODH_DATA}/aodh.conf &> ${AODH_DATA}/out &
# Wait for Aodh to start
wait_for_line "Running on http://0.0.0.0:8042/" ${AODH_DATA}/out
export AODH_ENDPOINT=http://localhost:8042/


mkfifo ${GNOCCHI_DATA}/out
cat > ${GNOCCHI_DATA}/gnocchi.conf <<EOF
[oslo_policy]
policy_file = ${VIRTUAL_ENV}/etc/gnocchi/policy.json
[api]
paste_config = ${VIRTUAL_ENV}/etc/gnocchi/api-paste.ini
[storage]
metric_processing_delay = 1
file_basepath = ${GNOCCHI_DATA}
driver = file
coordination_url = file://${GNOCCHI_DATA}
[indexer]
url = $GNOCCHI_TEST_INDEXER_URL
EOF
gnocchi-upgrade --config-file ${GNOCCHI_DATA}/gnocchi.conf
gnocchi-metricd --config-file ${GNOCCHI_DATA}/gnocchi.conf &>/dev/null &
gnocchi-api --config-file ${GNOCCHI_DATA}/gnocchi.conf &> ${GNOCCHI_DATA}/out &
# Wait for Gnocchi to start
wait_for_line "Running on http://0.0.0.0:8041/" ${GNOCCHI_DATA}/out

export GNOCCHI_ENDPOINT=http://localhost:8041/

# gnocchi alarms validate existence
curl -X POST -H 'Content-Type:application/json' ${GNOCCHI_ENDPOINT}v1/resource/instance --data '{
  "display_name": "myvm",
  "flavor_id": "2", "host": "blah",
  "id": "6868DA77-FA82-4E67-ABA9-270C5AE8CBCA",
  "image_ref": "http://image",
  "project_id": "BD3A1E52-1C62-44CB-BF04-660BD88CD74D",
  "user_id": "BD3A1E52-1C62-44CB-BF04-660BD88CD74D"
}'

$*
