#ifndef EVENT_BASE_H
#define EVENT_BASE_H

class Connection;

class EventBase {
public:
	explicit EventBase(int max_event);
	~EventBase();

	int event_add(Connection* conn);
	int event_del(Connection* conn);
	int event_wait(int timeout);

	int event_loop();
	int event_dispatch(Connection* conn, uint32_t event);

public:
	uint32_t 	ep;
	struct epoll_event *event;
	uint32_t 	nevent;
	uint32_t 	mtimeout;

private:
	EventBase(EventBase &edis);
	void operator=(EventBase &edis);
};

#endif
