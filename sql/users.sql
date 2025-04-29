IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'users')
BEGIN
    CREATE TABLE users (
        id INT PRIMARY KEY IDENTITY(1,1),
        username NVARCHAR(50) NOT NULL UNIQUE,
        email NVARCHAR(100) NOT NULL UNIQUE,
        created_at DATETIME2 DEFAULT GETUTCDATE()
    );
    PRINT 'Table "users" created successfully.';
END
ELSE
BEGIN
    PRINT 'Table "users" already exists.';
END
