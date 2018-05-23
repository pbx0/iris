from __future__ import absolute_import

import datetime
import logging
import ujson
from falcon import HTTP_201, HTTPBadRequest, HTTPNotFound

from iris import db

logger = logging.getLogger(__name__)


class rackspace(object):
    allow_read_no_auth = False

    def validate_post(self, body):
        if not all(k in body for k in("version", "status", "alerts")):
            raise HTTPBadRequest('missing version, status and/or alert attributes')

        if 'iris_plan' not in body["metadata"]:
            raise HTTPBadRequest('missing iris_plan key in metadata')

    def create_context(self, body):
        context_json_str = ujson.dumps(body)
        if len(context_json_str) > 65535:
            logger.warn('POST from rackspace exceeded acceptable size')
            raise HTTPBadRequest('Context too long')

        return context_json_str

    def on_post(self, req, resp):
        ''' 
        This endpoint is compatible with the webhook posts from Rackspace.
        Configure a Rackspace notification to include the name of an iris plan
        in a key called 'iris_plan' under the metadata section. You must
        configure this via the API and not the web console. See the docs here:

        https://developer.rackspace.com/docs/rackspace-monitoring/v1/api-reference/notifications-operations/

        You should end up making a request to create a notification in Rackspace with a body that looks like:
        {
          "label": "my webhook #1",
          "type": "webhook",
          "details": {
            "url": "http://iris:16649/v0/webhooks/alertmanager?application=test-app&key=abc"
          }
          "metadata": {
            "iris_plan": "teamA"
          }
        }

        Where application points to an application and key in Iris.

        For every POST from Rackspace, a new incident will be created, if the iris_plan label
        is attached to an notification from Rackspace.
        '''
        rack_params = ujson.loads(req.context['body'])
        self.validate_post(rack_params)

        with db.guarded_session() as session:
            plan = alert_params['metadata']['iris_plan']
            plan_id = session.execute('SELECT `plan_id` FROM `plan_active` WHERE `name` = :plan',
                                      {'plan': plan}).scalar()
            if not plan_id:
                raise HTTPNotFound()

            app = req.context['app']

            context_json_str = self.create_context(rack_params)

            app_template_count = session.execute('''
                SELECT EXISTS (
                  SELECT 1 FROM
                  `plan_notification`
                  JOIN `template` ON `template`.`name` = `plan_notification`.`template`
                  JOIN `template_content` ON `template_content`.`template_id` = `template`.`id`
                  WHERE `plan_notification`.`plan_id` = :plan_id
                  AND `template_content`.`application_id` = :app_id
                )
            ''', {'app_id': app['id'], 'plan_id': plan_id}).scalar()

            if not app_template_count:
                logger.warn('no plan template exists for this app')
                raise HTTPBadRequest('No plan template actions exist for this app')

            data = {
                'plan_id': plan_id,
                'created': datetime.datetime.utcnow(),
                'application_id': app['id'],
                'context': context_json_str,
                'current_step': 0,
                'active': True,
            }

            incident_id = session.execute(
                '''INSERT INTO `incident` (`plan_id`, `created`, `context`,
                                           `current_step`, `active`, `application_id`)
                   VALUES (:plan_id, :created, :context, 0, :active, :application_id)''',
                data).lastrowid

            session.commit()
            session.close()

        resp.status = HTTP_201
        resp.set_header('Location', '/incidents/%s' % incident_id)
        resp.body = ujson.dumps(incident_id)
