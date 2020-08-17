import falcon
import arcGIStest
import json
import threading

GIS = arcGIStest.ArcGISservices()

DBservice = arcGIStest.DBservices()
"""thread = threading.Thread(target=GIS.auto_update, args=('stations_process',))
thread.start()"""


def set_response(resp, body, status=falcon.HTTP_OK, content_type=falcon.MEDIA_JSON):
    resp.body = body
    resp.status = status
    resp.content_type = content_type


class RoutingServiceToken(object):
    def on_get(self, req, resp):
        item = GIS.get_routing_service_token()
        set_response(resp, json.dumps(item))


class SpatialAnalysisCalculation(object):
    def on_post(self, req, resp):
        data = json.loads(req.stream.read())
        item = GIS.spatial_analysis(data['task'], data['params'])
        set_response(resp, json.dumps(item))


class EditLayer(object):
    def on_put(self, req, resp):
        data = json.loads(req.stream.read())
        if data['action'] == 'adds':
            item = GIS.create_feature(data['elements'], data['layerName'])
            set_response(resp, json.dumps(item))
        elif data['action'] == 'deletes':
            item = GIS.remove_feature(data['elements'], data['layerName'])
            set_response(resp, json.dumps(item))
        elif data['action'] == 'deleteAll':
            item = GIS.remove_all_feature(data['layerName'])
            set_response(resp, json.dumps(item))
        elif data['action'] == 'updates':
            item = GIS.update_feature(data['elements'], data['layerName'])
            set_response(resp, json.dumps(item))
        else:
            set_response(status=falcon.HTTP_METHOD_NOT_ALLOWED)


class GetStations(object):
    def on_get(self, req, resp):
        item = DBservice.getStations(req.params.get('id'))
        set_response(resp, json.dumps(item))
