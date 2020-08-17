from arcgis.gis import GIS
import requests
import time
import random
import json


class ArcGISservices:

    def __init__(self):
        self.username = 'med.persee'
        self.password = 'Couscous1789'
        self.GIS = GIS("https://www.arcgis.com", self.username, self.password)

    def get_layer_with_name(self, layer_name):
        query = 'title: "{}*" AND type: "Feature Service"'.format(str(layer_name))
        search_results = self.GIS.content.search(query=query, max_items=10)
        return search_results[-1].layers[-1]

    def create_feature_layer(self, attributes, data_file_location):
        try:
            test_shp = self.GIS.content.add(attributes, data=data_file_location)
            return test_shp.publish()
        except Exception as e:
            print("Couldn't create the feature layer. {}".format(str(e)))

    def create_feature(self, features_to_add, layer_name):
        feature_layer = self.get_layer_with_name(layer_name=layer_name)
        try:
            return feature_layer.edit_features(adds=features_to_add)
        except Exception as e:
            return "Couldn't create the feature. {}".format(str(e))

    def remove_feature(self, feature_ids, layer_name):
        feature_layer = self.get_layer_with_name(layer_name=layer_name)
        try:
            return feature_layer.edit_features(deletes=feature_ids)
        except Exception as e:
            return "Couldn't delete the features. {}".format(str(e))

    def remove_all_feature(self, layer_name):
        feature_layer = self.get_layer_with_name(layer_name=layer_name)
        try:
            return feature_layer.delete_features()
        except Exception as e:
            return "Couldn't delete the features. {}".format(str(e))

    def update_feature(self, features_to_update, layer_name):
        feature_layer = self.get_layer_with_name(layer_name=layer_name)
        try:
            return feature_layer.edit_features(updates=features_to_update)
        except Exception as e:
            return "Couldn't update the features. {}".format(str(e))

    def get_routing_service_token(self):
        url = "https://www.arcgis.com/sharing/rest/oauth2/token"
        payload = "client_id=SFBgoA9DmDLGlhH8" \
                  "&client_secret=4b7089e490694a5eb106937c13b5b42f" \
                  "&grant_type=client_credentials"
        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'accept': "application/json",
            'cache-control': "no-cache",
        }

        return requests.request("POST", url, data=payload, headers=headers).json()

    def get_analysis_service_token(self, portal_url):
        """ Returns an authentication token for use in ArcGIS Online."""

        # Set the username and password parameters before
        #  getting the token.
        #
        token_url = "{}/generateToken".format(portal_url)
        params = "username={}&password={}&referer=http://www.arcgis.com&f=json" \
            .format(self.username, self.password)
        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'accept': "application/json",
            'cache-control': "no-cache",
        }

        response = requests.request("POST", token_url, data=params, headers=headers).json()
        if 'token' in response.keys():
            print("Getting token...")
            return response.get("token")
        else:
            if 'error' in response.keys():
                if response['error']['message'] == "This request needs to be made over https.":
                    response = requests.request("POST", token_url.replace("http://", "https://"),
                                                data=params, headers=headers).json()
                    return response.get('token')
                else:
                    raise Exception("Portal error: {} ".format(response['error']['message']))

    def get_analysis_url(self, portal_url, token):
        """ Returns Analysis URL from AGOL for running analysis services."""

        print("Getting Analysis URL...")
        portals_self_url = "{}/portals/self?f=json&token={}".format(portal_url, token)
        portal_response = requests.request("GET", portals_self_url).json()

        if portal_response.get("helperServices"):
            helper_services = portal_response.get("helperServices")
            if helper_services.get("analysis"):
                analysis_service = helper_services.get("analysis")
                if analysis_service.get("url"):
                    return analysis_service.get("url")
        else:
            raise Exception("Unable to obtain Analysis URL.")

    def analysis_job(self, analysis_url, task, token, params):
        """ Submits an Analysis job and returns the job URL for monitoring the job
            status in addition to the json response data for the submitted job."""

        # Unpack the Analysis job parameters as a dictionary and add token and
        # formatting parameters to the dictionary. The dictionary is used in the
        # HTTP POST request. Headers are also added as a dictionary to be included
        # with the POST.
        #
        print("Submitting analysis job...")

        headers = {"Referer": "http://www.arcgis.com", "Content-Type": "application/x-www-form-urlencoded"}
        task_url = "{}/{}".format(analysis_url, task)
        submit_url = "{}/submitJob?f=json&token={}".format(task_url, token)
        for (index, key) in enumerate(params.keys()):
            submit_url += "&{}={}".format(key, str(params[key]))
        analysis_response = requests.request(method='GET', url=submit_url, headers=headers).json()
        if analysis_response.get('jobId'):
            return {'task_url': task_url, 'job': analysis_response}
        else:
            raise Exception("Unable to submit analysis job.")

    def analysis_job_status(self, task_url, job_info, token):
        """ Tracks the status of the submitted Analysis job."""

        if job_info.get('jobId'):
            # Get the id of the Analysis job to track the status.
            #
            job_id = job_info.get('jobId')
            job_url = "{}/jobs/{}?f=json&token={}".format(task_url, job_id, token)
            job_response = requests.request(method='GET', url=job_url).json()

            if job_response.get('jobStatus'):
                while not job_response.get('jobStatus') == 'esriJobSucceeded':
                    time.sleep(5)
                    job_response = requests.request(method='GET', url=job_url).json()
                    print(job_response.get('jobStatus'))

                    if job_response.get('jobStatus') == 'esriJobFailed':
                        raise Exception('Job failed.')
                    elif job_response.get('jobStatus') == 'esriJobCancelled':
                        raise Exception('Job cancelled.')
                    elif job_response.get('jobStatus') == 'esriJobTimedOut':
                        raise Exception('Job timed out.')
                if job_response.get('results'):
                    return job_response
            else:
                raise Exception("No job results.")
        else:
            raise Exception("No job url.")

    def analysis_job_results(self, task_url, job_info, token):
        """ Use the job result json to get information about the feature service
            created from the Analysis job."""

        # Get the paramUrl to get information about the Analysis job results.
        #
        if job_info.get('jobId'):
            job_id = job_info.get('jobId')
            if job_info.get('results'):
                results = job_info.get('results')
                result_values = {}
                for key in list(results.keys()):
                    param_value = results[key]
                    if param_value.get('paramUrl'):
                        param_url = param_value.get('paramUrl')
                        result_url = "{}/jobs/{}/{}?token={}&f=json".format(task_url,
                                                                            job_id,
                                                                            param_url,
                                                                            token)
                        request_results = requests.request(method='GET', url=result_url).json()
                        job_value = request_results.get('value')
                        result_values[key] = job_value
                return result_values
            else:
                raise Exception("Unable to get analysis job results.")
        else:
            raise Exception("Unable to get analysis job results.")

    def spatial_analysis(self, task, parameters):

        token = self.get_analysis_service_token('https://www.arcgis.com/sharing/rest')
        analysis_url = (self.get_analysis_url('https://www.arcgis.com/sharing/rest', token))
        analysis_job = self.analysis_job(analysis_url, task, token, parameters)
        job_response = self.analysis_job_status(analysis_job.get('task_url'), analysis_job.get('job'), token)
        return self.analysis_job_results(analysis_job.get('task_url'), job_response, token)

    def auto_update(self, layerName):
        while True:
            print('updated layer')
            new_values = [
                {
                    "attributes": {
                        "ObjectId": 1,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 2,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 3,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 4,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 5,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 6,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 7,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 8,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 9,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 10,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 11,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 12,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 13,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 14,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 15,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 16,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 17,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 18,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                },
                {
                    "attributes": {
                        "ObjectId": 19,
                        "vehicles_at_station": random.randint(0, 15)
                    }
                }
            ]
            self.update_feature(new_values, layerName)
            time.sleep(60)


class DBservices:

    def getStations(self, station_id=None):
        stations = json.load(open('data/mockedUpFr.json'))
        if station_id:
            return next(filter(lambda station: station['id'] == int(station_id), stations))
        return stations
