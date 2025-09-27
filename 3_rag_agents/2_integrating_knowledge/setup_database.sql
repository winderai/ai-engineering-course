CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    source TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO documents (source, content) VALUES
    ('email', 'Order confirmation for 500 units of IPA'),
    ('slack', 'Brewery maintenance scheduled for Tuesday'),
    ('api', 'Current fermentation tank temperature: 68°F');

SELECT * FROM documents;