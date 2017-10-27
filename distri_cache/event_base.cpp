#include <sys/epoll.h>
#include "event_base.h"

EventBase::EventBase(int max_event, int timeout)
	: ep(-1),
	  events(NULL),
	  nevent(max_event),
	  mtimeout(timeout)
{
}

EventBase::~EventBase()
{
}

int EventBase::create()
{
	ep = epoll_create(1);
	if(ep < 0) {
		printf("epoll create failed : %s\n", strerror(errno));
		return -1;
	}

	events = malloc(sizeof(struct epoll_event) * nevent);
	if(events == NULL) {
		close(ep);
		printf("malloc events failed\n");
		return -1;
	}

	return 0;
}

int EventBase::destroy()
{
	if(ep > 0) {
		close(ep);
	}
	ep = -1;
	if(events) {
		free(events);
		events = NULL;
	}
	nevent = 0;
}

int EventBase::event_add(Connection *conn)
{
	int status;
	struct epoll_event event;

	event.events = (uint32_t)(EPOLLIN | EPOLLOUT | EPOLLET);
	event.data.ptr = conn;

	status = epoll_ctl(ep, EPOLL_CTL_ADD, conn->fd, &event);
	if(status < 0) {
		printf("epoll_ctl add event failed: %s\n", strerror(errno));
	}

	return status;
}

int EventBase::event_del(Connection *conn)
{
	int status;
	
	status = epoll_ctl(ep, EPOLL_CTL_DEL, conn->fd, NULL);
	if(status < 0) {
		printf("epoll_ctl del event failed: %s\n", strerror(errno));
	}

	return status;
}

int EventBase::event_wait(int timeout)
{
	int i;
	int nfd;

	for(;;) {
		nfd = -1;
		nfd = epoll_wait(ep, events, nevent, timeout);
		if(nfd > 0) {
			for(i = 0; i < nfd; i++) {
				uint32_t event;

				if(events[i].events & EPOLLER) {
					event |= EVENT_ERR;
				}

				if(events[i].events & (EPOLLIN | EPOLLHUP)) {
					event |= EVENT_READ;
				}

				if(event[i].events & EPOLLOUT) {
					event |= EVENT_WRITE;
				}

				event_dispatch(events[i].data.ptr, event);
			}

			return nfd;
		}

		if(nfd == 0) {
			printf("epoll_wait timeout : %d\n", timeout);
			return 0;
		}

		if(errno == EINTR) {
			continue;
		}

		return -1;
	}
}

void EventBase::event_loop()
{
	int status;
	for(;;) {
		status = event_wait(mtimeout);
		if(status < 0) {
			printf("event_loop exit\n");
			break;
		}
	}
}

int EventBase::event_dispatch(Connection* conn, uint32_t event)
{
	int status = -1;
	if(event & EVENT_ERR) {
		return status;
	}

	if(event & EVENT_READ) {
		status = conn->read();
		if(status < 0) {
			printf("event_read fail\n");
			return status;
		}
	}

	if(event & EVENT_WRITE) {
		status = conn->write();
		if(status < 0) {
			printf("event_write fail\n");
			return status;
		}
	}

	return status;
}
