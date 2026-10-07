## 1:
        repeatedly doing:
        TCP connection
        → AMQP negotiation
        → authentication
        → channel creation
        → publish
        → teardown
        for every request.


## 2:
        maintain a global statistics report.

## 3: 
        should a poll on queued return 200 with status queued?