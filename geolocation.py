import googlemaps


class GeoLocation:

    @staticmethod
    def get_nearest_office_lat_lon(origin, gcp_token):
        gmaps = googlemaps.Client(key=gcp_token)

        kharkiv_offices_lat_lon = [
            ('50.060574844559866', '36.20606569639297'),  # Перемога
            ('50.04691905211412', '36.28969164172298'),  # Жуковскького
            ('50.0255722981472', '36.33484871613497'),  # Героїв праці
            ('49.947870249860244', '36.40416140769709'),  # Індустріальна
            ('49.934451893936405', '36.2444276293161'),  # Основа
            ('49.956958446293996', '36.20470856889871'),  # Новожанове
            ('49.98465564704916', '36.1751342720858'),  # Холодна гора
            ('49.99238073975426', '36.22972782854143')  # Історичний музей
        ]

        distances_durations = gmaps.distance_matrix(
            origins=origin,
            destinations=kharkiv_offices_lat_lon
        )['rows'][0]['elements']  # TODO if zero elements  [{'status': 'ZERO_RESULTS'}, {'status': 'ZERO_RESULTS'}, {'status': 'ZERO_RESULTS'}, {'status': 'ZERO_RESULTS'}, {'status': 'ZERO_RESULTS'}, {'status': 'ZERO_RESULTS'}, {'status': 'ZERO_RESULTS'}, {'status': 'ZERO_RESULTS'}]

        zero_results_num = 0
        for result in distances_durations:
            if result['status'] == 'ZERO_RESULTS':
                zero_results_num += 1
        if len(distances_durations) == zero_results_num:
            return 'Неможливо побудувати маршрут!'

        distance_texts = []  # human readable value, e.g. '8.8 km'
        distance_values = []  # in meters, e.g. 8786
        for row in distances_durations:
            distance_texts.append(row['distance']['text'])
            distance_values.append(row['distance']['value'])

        index_nearest = min(range(len(distance_values)), key=distance_values.__getitem__)
        nearest_location = kharkiv_offices_lat_lon[index_nearest]
        distance_to = distance_texts[index_nearest]
        return nearest_location, distance_to

    @staticmethod
    def get_url_from_lat_lon(origin, destination):
        orig_lon, orig_lat = origin[0], origin[1]
        dest_lon, dest_lat = destination[0], destination[1]
        return f'https://www.google.com/maps/dir/{orig_lon},{orig_lat}/{dest_lon},{dest_lat}/'