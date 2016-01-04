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
MYSQL_DATA=`mktemp -d /tmp/aodh-mysql-XXXXX`
trap "clean_exit \"$AODH_DATA\" \"$MYSQL_DATA\"" EXIT

mysqld --initialize-insecure --datadir=${MYSQL_DATA} || true
mkfifo ${MYSQL_DATA}/out
PATH=$PATH:/usr/libexec
mysqld --no-defaults --datadir=${MYSQL_DATA} --pid-file=${MYSQL_DATA}/mysql.pid --socket=${MYSQL_DATA}/mysql.socket --skip-networking --skip-grant-tables &> ${MYSQL_DATA}/out &
# Wait for MySQL to start listening to connections
wait_for_line "mysqld: ready for connections." ${MYSQL_DATA}/out
export AODH_TEST_STORAGE_URL="mysql+pymysql://root@localhost/test?unix_socket=${MYSQL_DATA}/mysql.socket&charset=utf8"
mysql --no-defaults -S ${MYSQL_DATA}/mysql.socket -e 'CREATE DATABASE test;'


mkfifo ${AODH_DATA}/out
echo '{"default": ""}' > ${AODH_DATA}/policy.json
cat > ${AODH_DATA}/aodh.conf <<EOF
[api]
paste_config = ${AODH_DATA}/api-paste.ini
[oslo_policy]
policy_file = ${AODH_DATA}/policy.json
[database]
connection = mysql+pymysql://root@localhost/test?unix_socket=${MYSQL_DATA}/mysql.socket&charset=utf8
EOF
cat <<EOF > ${AODH_DATA}/api-paste.ini
[pipeline:main]
pipeline = aodh
[app:aodh]
paste.app_factory = aodh.api.app:app_factory
EOF
aodh-dbsync --config-file ${AODH_DATA}/aodh.conf
aodh-api --config-file ${AODH_DATA}/aodh.conf &> ${AODH_DATA}/out &
# Wait for Aodh to start
wait_for_line "Running on http://0.0.0.0:8042/" ${AODH_DATA}/out
export AODH_ENDPOINT=http://localhost:8042/

$*
