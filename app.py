from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'  # change to something secure
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# -------------------
# MODELS
# -------------------

class Event(db.Model):
    __tablename__ = 'events'
    event_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text)

    allocations = db.relationship('EventResourceAllocation',
                                  back_populates='event',
                                  cascade='all, delete-orphan')

    def duration_hours(self):
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600.0


class Resource(db.Model):
    __tablename__ = 'resources'
    resource_id = db.Column(db.Integer, primary_key=True)
    resource_name = db.Column(db.String(200), nullable=False)
    resource_type = db.Column(db.String(100), nullable=False)

    allocations = db.relationship('EventResourceAllocation',
                                  back_populates='resource',
                                  cascade='all, delete-orphan')


class EventResourceAllocation(db.Model):
    __tablename__ = 'event_resource_allocations'
    allocation_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.resource_id'), nullable=False)

    event = db.relationship('Event', back_populates='allocations')
    resource = db.relationship('Resource', back_populates='allocations')


# -------------------
# UTILITY FUNCTIONS
# -------------------

def parse_datetime_from_form(field_name):
    """
    HTML datetime-local gives a string like '2025-12-10T14:30'.
    Convert to Python datetime.
    """
    value = request.form.get(field_name)
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M")


def check_conflicts(event, resource_ids):
    """
    Check if the given event (new or edited) conflicts with existing allocations
    for the given list of resource_ids.

    Conflict rule for time: Overlap exists if:
        new_start < existing_end AND new_end > existing_start
    """
    conflicts = []

    if event.start_time >= event.end_time:
        conflicts.append("Event start time must be before end time.")
        return conflicts

    for resource_id in resource_ids:
        # For this resource, get all other events that use it
        allocations = EventResourceAllocation.query.filter_by(resource_id=resource_id).all()
        for alloc in allocations:
            other_event = alloc.event
            if other_event.event_id == event.event_id:
                # skip self when editing
                continue

            # Overlap condition
            if (event.start_time < other_event.end_time and
                    event.end_time > other_event.start_time):
                conflicts.append(
                    f"Resource '{alloc.resource.resource_name}' "
                    f"is already booked by event '{other_event.title}' "
                    f"from {other_event.start_time} to {other_event.end_time}."
                )
    return conflicts


# -------------------
# ROUTES - HOME
# -------------------

@app.route('/')
def index():
    # small dashboard data for home page
    upcoming_events = Event.query.order_by(Event.start_time).limit(3).all()
    events_count = Event.query.count()
    resources_count = Resource.query.count()
    return render_template(
        'home.html',
        upcoming_events=upcoming_events,
        events_count=events_count,
        resources_count=resources_count
    )



# -------------------
# ROUTES - RESOURCES
# -------------------

@app.route('/resources')
def list_resources():
    resources = Resource.query.all()
    return render_template('resources.html', resources=resources)


@app.route('/resources/add', methods=['GET', 'POST'])
def add_resource():
    if request.method == 'POST':
        name = request.form.get('resource_name')
        rtype = request.form.get('resource_type')

        if not name or not rtype:
            flash("Resource name and type are required.", "danger")
            return redirect(url_for('add_resource'))

        resource = Resource(resource_name=name, resource_type=rtype)
        db.session.add(resource)
        db.session.commit()
        flash("Resource added successfully!", "success")
        return redirect(url_for('list_resources'))

    return render_template('resource_form.html', action="Add")


@app.route('/resources/edit/<int:resource_id>', methods=['GET', 'POST'])
def edit_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    if request.method == 'POST':
        resource.resource_name = request.form.get('resource_name')
        resource.resource_type = request.form.get('resource_type')

        if not resource.resource_name or not resource.resource_type:
            flash("Resource name and type are required.", "danger")
            return redirect(url_for('edit_resource', resource_id=resource_id))

        db.session.commit()
        flash("Resource updated successfully!", "success")
        return redirect(url_for('list_resources'))

    return render_template('resource_form.html', action="Edit", resource=resource)


# -------------------
# ROUTES - EVENTS
# -------------------

@app.route('/events')
def list_events():
    events = Event.query.order_by(Event.start_time).all()
    resources = Resource.query.all()
    return render_template('events.html', events=events, resources=resources)


@app.route('/events/add', methods=['GET', 'POST'])
def add_event():
    resources = Resource.query.all()
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_time = parse_datetime_from_form('start_time')
        end_time = parse_datetime_from_form('end_time')
        selected_resource_ids = request.form.getlist('resources')  # list of strings

        if not title or not start_time or not end_time:
            flash("Title, start time, and end time are required.", "danger")
            return redirect(url_for('add_event'))

        # Create an unsaved Event object to run conflict checks
        event = Event(title=title,
                      description=description,
                      start_time=start_time,
                      end_time=end_time)

        # Convert resource IDs to ints
        resource_ids = [int(rid) for rid in selected_resource_ids]

        # Conflict check
        conflicts = check_conflicts(event, resource_ids)
        if conflicts:
            for c in conflicts:
                flash(c, "danger")
            return render_template('event_form.html',
                                   action="Add",
                                   resources=resources,
                                   event=event,
                                   selected_resource_ids=resource_ids)

        # Save event
        db.session.add(event)
        db.session.flush()  # get event_id before commit

        for rid in resource_ids:
            alloc = EventResourceAllocation(event_id=event.event_id, resource_id=rid)
            db.session.add(alloc)

        db.session.commit()
        flash("Event added successfully!", "success")
        return redirect(url_for('list_events'))

    return render_template('event_form.html', action="Add", resources=resources)


@app.route('/events/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    resources = Resource.query.all()

    if request.method == 'POST':
        event.title = request.form.get('title')
        event.description = request.form.get('description')
        event.start_time = parse_datetime_from_form('start_time')
        event.end_time = parse_datetime_from_form('end_time')
        selected_resource_ids = [int(rid) for rid in request.form.getlist('resources')]

        if not event.title or not event.start_time or not event.end_time:
            flash("Title, start time, and end time are required.", "danger")
            return redirect(url_for('edit_event', event_id=event_id))

        conflicts = check_conflicts(event, selected_resource_ids)
        if conflicts:
            for c in conflicts:
                flash(c, "danger")
            return render_template('event_form.html',
                                   action="Edit",
                                   resources=resources,
                                   event=event,
                                   selected_resource_ids=selected_resource_ids)

        # Clear old allocations and add new ones
        EventResourceAllocation.query.filter_by(event_id=event.event_id).delete()
        for rid in selected_resource_ids:
            db.session.add(EventResourceAllocation(event_id=event.event_id,
                                                   resource_id=rid))

        db.session.commit()
        flash("Event updated successfully!", "success")
        return redirect(url_for('list_events'))

    selected_resource_ids = [alloc.resource_id for alloc in event.allocations]
    return render_template('event_form.html',
                           action="Edit",
                           resources=resources,
                           event=event,
                           selected_resource_ids=selected_resource_ids)


# -------------------
# ROUTES - CONFLICT VIEW
# -------------------

@app.route('/conflicts')
def conflict_view():
    """
    Scan all allocations and show any conflicting bookings.
    """
    conflicts = []
    allocations = EventResourceAllocation.query.all()

    # naive O(n^2) check – fine for small assignment data
    for i in range(len(allocations)):
        for j in range(i + 1, len(allocations)):
            a1 = allocations[i]
            a2 = allocations[j]
            if a1.resource_id != a2.resource_id:
                continue

            e1 = a1.event
            e2 = a2.event

            # Overlap check
            if (e1.start_time < e2.end_time and
                    e1.end_time > e2.start_time):
                conflicts.append({
                    "resource": a1.resource.resource_name,
                    "event1": e1,
                    "event2": e2
                })

    return render_template('conflicts.html', conflicts=conflicts)


# -------------------
# ROUTES - UTILISATION REPORT
# -------------------

@app.route('/report', methods=['GET', 'POST'])
def utilisation_report():
    resources = Resource.query.all()
    report_data = []
    upcoming = []

    start_str = end_str = None

    if request.method == 'POST':
        start_str = request.form.get('start_date')
        end_str = request.form.get('end_date')

        if not start_str or not end_str:
            flash("Start date and end date are required.", "danger")
            return render_template('report.html',
                                   resources=resources,
                                   report_data=report_data,
                                   upcoming=upcoming,
                                   start_date=start_str,
                                   end_date=end_str)

        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        # end of the day
        end_date = datetime.strptime(end_str, "%Y-%m-%d")
        end_date = datetime.combine(end_date.date(), datetime.max.time())

        for resource in resources:
            # get all events allocated to this resource that overlap range
            allocations = resource.allocations
            total_hours = 0.0
            resource_upcoming = []

            for alloc in allocations:
                event = alloc.event
                # check overlap with [start_date, end_date]
                if event.start_time <= end_date and event.end_time >= start_date:
                    # overlapped window
                    overlap_start = max(event.start_time, start_date)
                    overlap_end = min(event.end_time, end_date)
                    if overlap_start < overlap_end:
                        hours = (overlap_end - overlap_start).total_seconds() / 3600.0
                        total_hours += hours

                    # upcoming booking (in future from now)
                    if event.start_time >= datetime.now():
                        resource_upcoming.append(event)

            report_data.append({
                "resource": resource,
                "total_hours": round(total_hours, 2),
                "upcoming": sorted(resource_upcoming, key=lambda e: e.start_time)
            })

        # Flatten some upcoming info if you want a combined list as well
        for r in report_data:
            for ev in r["upcoming"]:
                upcoming.append({"resource": r["resource"], "event": ev})

    return render_template('report.html',
                           resources=resources,
                           report_data=report_data,
                           upcoming=upcoming,
                           start_date=start_str,
                           end_date=end_str)


# -------------------
# DB INIT
# -------------------

@app.cli.command('init-db')
def init_db():
    """Flask CLI command: flask init-db"""
    db.create_all()
    print("Database initialised.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
