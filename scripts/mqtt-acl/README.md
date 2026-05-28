# MQTT ACL Templates

Áp dụng để hardening **INT-C1** (MQTT topic injection).

| File | Broker |
|------|--------|
| `mosquitto_acl.conf` | Mosquitto (anyone) |
| `emqx_acl_rules.json` | EMQX 5.x dashboard / API |

## Mosquitto

```bash
docker cp mosquitto_acl.conf xiaozhi-mqtt:/mosquitto/config/acl.conf
# Cập nhật /mosquitto/config/mosquitto.conf:
#   allow_anonymous false
#   password_file /mosquitto/config/passwd
#   acl_file /mosquitto/config/acl.conf
docker compose restart xiaozhi-mqtt
```

Verify (must be DENIED):

```bash
mosquitto_sub -h localhost -p 1883 -u xiaozhi_device -P "$MQTT_DEVICE_PASSWORD" \
    -i ATTACKER_ALICE -t 'device/+/server' -d
# → Connection denied
```

Verify (must be ALLOWED — own topic):

```bash
mosquitto_sub -h localhost -p 1883 -u xiaozhi_device -P "$MQTT_DEVICE_PASSWORD" \
    -i ATTACKER_ALICE -t 'device/ATTACKER_ALICE/server' -d
# → Connected; subscription accepted
```

## EMQX

```bash
curl -u admin:public -X POST http://localhost:18083/api/v5/authorization/sources/built_in_database/rules/users \
    -H 'Content-Type: application/json' \
    -d @emqx_acl_rules.json
```

Hoặc Dashboard → **Access Control → Authorization → Built-in Database** → import file.

Đảm bảo nguồn ACL `built_in_database` được kích hoạt và sắp xếp **trước** mọi rule allow-all.
