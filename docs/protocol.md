# SFS2X protocol reference

Controller IDs, system action codes and the SFSObject-key conventions
used by the wire format. These are mainly useful when you need to call
`Message(...)` directly or define your own custom `SystemRequest` /
`SystemResponse` models.

## `ControllerID`

| Value | Name           | Purpose                                  |
|-------|----------------|------------------------------------------|
| 0     | `SYSTEM`       | Handshake, login, rooms, messages, users |
| 1     | `EXTENSION`    | Custom extension commands                |
| 2     | `SECURITY`     | UDP / encryption negotiation             |
| 3     | `BUDDY`        | Buddy list management                    |
| 4     | `ROOM_MANAGER` | Room creation / destruction              |
| 5     | `ADMIN`        | Admin tool & console commands            |

## `SysAction`

| Code | Name                         |
|------|------------------------------|
| 0    | `HANDSHAKE`                  |
| 1    | `LOGIN`                      |
| 2    | `LOGOUT`                     |
| 3    | `GET_ROOM_LIST`              |
| 4    | `JOIN_ROOM`                  |
| 5    | `AUTO_JOIN`                  |
| 6    | `CREATE_ROOM`                |
| 7    | `GENERIC_MESSAGE`            |
| 8    | `CHANGE_ROOM_NAME`           |
| 9    | `CHANGE_ROOM_PASSWORD`       |
| 10   | `OBJECT_MESSAGE`             |
| 11   | `SET_ROOM_VARIABLES`         |
| 12   | `SET_USER_VARIABLES`         |
| 13   | `CALL_EXTENSION`             |
| 14   | `LEAVE_ROOM`                 |
| 15   | `SUBSCRIBE_ROOM_GROUP`       |
| 16   | `UNSUBSCRIBE_ROOM_GROUP`     |
| 17   | `SPECTATOR_TO_PLAYER`        |
| 18   | `PLAYER_TO_SPECTATOR`        |
| 19   | `CHANGE_ROOM_CAPACITY`       |
| 20   | `PUBLIC_MESSAGE`             |
| 21   | `PRIVATE_MESSAGE`            |
| 22   | `MODERATOR_MESSAGE`          |
| 23   | `ADMIN_MESSAGE`              |
| 24   | `KICK_USER`                  |
| 25   | `BAN_USER`                   |
| 26   | `MANUAL_DISCONNECTION`       |
| 27   | `FIND_ROOMS`                 |
| 28   | `FIND_USERS`                 |
| 29   | `PING_PONG`                  |
| 30   | `SET_USER_POSITION`          |
| 31   | `QUICK_JOIN_OR_CREATE_ROOM`  |
| 200+ | Buddy actions                |
| 300+ | Game / invite actions        |
| 500+ | Cluster actions              |
| 1000+| Server-pushed event actions  |

## Wire envelope

Every `Message` is encoded as an `SFSObject` with these top-level keys:

| Key | Type      | Meaning                                    |
|-----|-----------|--------------------------------------------|
| `c` | `Byte`    | Controller ID                              |
| `a` | `Short`   | Action code (`SysAction` for `SYSTEM`)     |
| `p` | `SFSObject` | Action-specific parameters               |

## Extension envelope

Extension messages set `controller = EXTENSION` and `action = 12`. The
payload (`p` above) is itself an `SFSObject` with these keys:

| Key | Type        | Meaning                                                     |
|-----|-------------|-------------------------------------------------------------|
| `c` | `UtfString` | Extension command name (`"gs_pussy"`, `"join"`, …)          |
| `r` | `Int`       | Request id — echo it back in your reply for correlation. `-1` = no correlation. |
| `p` | `SFSObject` | Command-specific parameters                                  |

## Common payload keys (SFS2X conventions)

| Key   | Usual meaning             | Example actions       |
|-------|---------------------------|------------------------|
| `zn`  | Zone name                 | `LOGIN`, `LOGOUT`      |
| `un`  | Username                  | `LOGIN`                |
| `pw`  | Password                  | `LOGIN`                |
| `id`  | User id                   | `LOGIN` response       |
| `pi`  | Privilege id              | `LOGIN` response       |
| `ec`  | Error code                | error responses        |
| `em`  | Error message             | error responses        |
| `epr` | Error params              | error responses        |
| `api` | SFS API version           | `HANDSHAKE`            |
| `cl`  | Client identifier         | `HANDSHAKE`            |
| `bin` | Binary mode flag          | `HANDSHAKE`            |
| `tk`  | Session token             | `HANDSHAKE` response   |
| `ct`  | Compression threshold     | `HANDSHAKE` response   |
| `ms`  | Max message size          | `HANDSHAKE` response   |
