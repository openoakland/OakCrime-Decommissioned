from django.db import DatabaseError, connection

def health(_):
    """ Returns a simplified view of the health of this application.
    Checks the database connection. Use this for load balancer health checks.
    """
	
    def status_fmt(ok):
        return 'OK' if ok else 'UNAVAILABLE'

    try:
        cursor = connection.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        cursor.close()
        database_ok = True
    except DatabaseError:
        database_ok = False

    overall_ok = all((database_ok,))

    data = {
        'timestamp': timezone.now(),
        'overall_status': status_fmt(overall_ok),
        'detailed_status': {
            'database_status': status_fmt(database_ok),
        },
    }

    status = 200 if overall_ok else 503

    return JsonResponse(data, status=status)
