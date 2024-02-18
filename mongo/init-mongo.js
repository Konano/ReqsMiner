db.createUser(
    {
        user: 'nano',
        pwd: 'sjz9TGQp7khx1D0FLtvV',
        roles: [
            {
                role: 'readWrite',
                db: 'reqs-miner'
            }
        ]
    }
)

db.createCollection('request')
db.request.createIndex({ token: 1 }, { unique: true })

db.createCollection('diff')
