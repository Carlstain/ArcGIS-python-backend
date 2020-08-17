import falcon
import ressources
from falcon_cors import CORS
from waitress import serve


class Version(object):
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.body = "Version 0.1"


app = falcon.API(middleware=[
    CORS(
        allow_origins_list=["*"],
        allow_all_origins=True,
        allow_all_headers=True,
        allow_all_methods=True,
    ).middleware
])

app.req_options.strip_url_path_trailing_slash = True

app.add_route("/arc-api/v", Version())
app.add_route("/arc-api/routing-token", ressources.RoutingServiceToken())
app.add_route("/arc-api/spatial-analysis", ressources.SpatialAnalysisCalculation())
app.add_route("/arc-api/edit-layer", ressources.EditLayer())
app.add_route("/arc-api/stations", ressources.GetStations())
if __name__ == '__main__':
    serve(app=app, host='localhost', port=8181)
