#ifndef CONNECTION_H
#define CONNECTION_H

class Connection {
public:
	explicit Connection();
	virtual ~Connection() = 0;

	virtual read();
	virtual write();

private:
	int fd;

private:
	Connection(Connection &conn);
	void operator=(Connection &conn);
};


#endif