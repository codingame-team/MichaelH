import sys
import math
import email
# import urllib  as URLLIB, urllib3 , urllib_ext , urllib_parse_ParseResult_overloaded, urllib5
import os.path
from urllib import request, parse
import json
import requests
import re
from email import policy
from email.parser import BytesParser
from email.iterators import typed_subpart_iterator
from mapbox import Geocoder

#
# Created by philRG on 26/04/2020.
# Copyright © 2020 philRG. All rights reserved.
#

#
#   Paramètres globaux du programme
#

# ma clé d'API sur Mabox: https://account.mapbox.com/
MAPBOX_API_KEY = "pk.eyJ1IjoicG1vdXJleSIsImEiOiJjazlmcW5lMmEwZTFyM2RxbXhwd3l6eDdpIn0.0AxxOZigM-4EeTORmNAndA"

# Regénérer les coordonnées GPS du point de départ des taxis et des destinations usuelles (non utilisé pour l'instant)
TAXI_LOCATION_REBUILD = False
DESTINATION_LOCATION_REBUILD = False

# Chemins d'accès aux fichiers sur le PC
chemin = "C:\\Users\\User\\source\\repos\\MichaelH"
input_file = "Mail des resas.eml"
output_file = "Planning.csv"
gps_locations_file = "data\\locations_gps.txt"
taxis_file = "data\\taxis.txt"


#
# Quelques fonctions de vérification de l'encodage de caractères utilisé dans le mail (au cas où) - Peut-être à supprimer (car double emploi)
#
def get_charset(message, default="ascii"):
    """Get the message charset"""

    if message.get_content_charset():
        return message.get_content_charset()

    if message.get_charset():
        return message.get_charset()

    return default


def get_body(message):
    """Get the body of the email message"""

    if message.is_multipart():
        # get the plain text version only
        text_parts = [part for part in typed_subpart_iterator(message, 'text', 'plain')]
        body = []
        for part in text_parts:
            charset = get_charset(part, get_charset(message))
            body.append(str(part.get_payload(decode=True), charset, "replace"))

        return u"\n".join(body).strip()

    else:  # if it is not multipart, the payload will be a string
        # representing the message body
        body = str(message.get_payload(decode=True), get_charset(message), "replace")
        return body.strip()


#
# Les fonctions de géolocalisation pour OpenStreetMap, GoogleMaps (non utilisées dans ce programme)
#   (N.B.: j'ai choisi Mapbox cf classe DAO_Toolbox plus bas... (100.000 requêtes gratuites par mois) car GoogleMaps API est devenu payant et OpenStreetMap peu exploitable
#
# OpenStreet Map (données OpenData)
# https://nominatim.openstreetmap.org/search?q=17+Strada+Pictor+Alexandru+Romano%2C+Bukarest&format=geojson
# API Documentation: https://nominatim.org/release-docs/develop/api/Search/
# Fonction OpenStreet Map pour récupérer les coordonnées GPS d'une adresse donnée
# Imprécis! Ne localise pas le numéro de rue :-(
# Pas besoin de clé API
def get_GPS_Coordinates_OpenStreet_Map(postal_address, city):
    formatted_PA = postal_address.replace(" ", "+") + parse.quote(",") + "+" + city
    print(formatted_PA)
    # url_address = parse.urlencode(formatted_PA)
    # url_address = parse.quote(formatted_PA)
    # print(url_address)
    # url_openstreetmap_api = "https://nominatim.openstreetmap.org/search?q=" + url_address + "&key=" + MAPBOX_API_KEY
    url_openstreetmap_api = "https://nominatim.openstreetmap.org/search?q=" + formatted_PA + "&format=geojson"

    print(url_openstreetmap_api)
    # Request data from link as 'str'
    data = requests.get(url_openstreetmap_api).text

    # convert 'str' to Json
    data = json.loads(data)

    return data


# (Non utilisé) Récupérer une clé d'API pour la géolocalisation Google Maps (nécessite une CB, crédit de 200$ par mois): https://developers.google.com/maps/documentation/geocoding/get-api-key
GOOGLE_API_KEY = "AIzaSyBRcsCnUED0GjjM1Ex2nYayoGMSnBIehac"


def get_GPS_Coordinates_Google_API(postal_address):
    formatted_PA = postal_address
    url_address = parse.urlencode({'address': formatted_PA})
    url_google_map_api = "https://maps.googleapis.com/maps/api/geocode/json?address=" + url_address + "&key=" + GOOGLE_API_KEY

    # Request data from link as 'str'
    data = requests.get(url_google_map_api).text

    # convert 'str' to Json
    data = json.loads(data)

    # data = requests.get(url=url_google_map_api)
    # binary = data.content
    # output = json.loads(binary)

    # result = json.load(urllib.urlopen(url_google_map_api))
    return data


#
# Quelques fonctions de manipulation de chaînes de caractères
#
regex_dsup_delimiter = '>> ?\d{1,2} *'
regex_cr_lf = '[\n\r]'
regex_libelle_societe = '^-- TAXI MEDICAL NICE'
regex_code_secteur = 'S\d{1,2}'
regex_special_chars = '[^A-Za-z0-9 \-()<<]'
regex_phone_number = '([0-9]{2} ){4}'


def conversion_accents(chaine):
    converter = {'é': 'e', 'è': 'e', 'ê': 'e', 'à': 'a', 'ç': 'c'}
    result = ""
    for c in chaine:
        if c in converter:
            c = converter[c]
        result += c
    return result


#
# Description des objets sous forme de classe
#
class Taxi(object):
    #   Constructeur de la classe Taxi
    #   Paramètres d'initialisation:
    #       - Id (géré par l'application)
    #       - Nom (obligatoire?)
    #       - Id de localisation (géré par l'application)
    def __init__(self, id, name, id_location):
        self.id = id
        self.name = name
        self.id_location = id_location

    def __str__(self):
        return "{} (id:{}), name:{}, id_location:{}".format(self.__class__.__name__, self.id, self.name,
                                                            self.id_location)


#
# Description des classes métier et d'accès aux données
#   Objectif de l'abstraction: s'affranchir de la source de données, structurer des données provenant d'un système tiers, et séparer les différentes couches applicatives
#

#
# Classes métier "Location", "Taxi" et "Courses"
#
class Location(object):
    #   Constructeur de la classe Location
    #   Paramètres d'initialisation:
    #       - Id (géré par l'application)
    #       - Adresse postale (obligatoire)
    #       - Latitude (obligatoire?)
    #       - Longitude (obligatoire?)
    #       - Code secteur (facultatif)
    #       - Type d'emplacement (obligatoire) (adresse taxi, adresse de ramassage "pick-up" ou de destination): "T", "P", "D"
    def __init__(self, id, postal_address, latitude, longitude, sector_code, location_type):
        self.id = id
        self.postal_address = postal_address
        self.latitude = latitude
        self.longitude = longitude
        self.sector_code = sector_code
        self.location_type = location_type

    def __str__(self):
        return "{} (id:{}), latitude:{}, longitude:{}".format(self.__class__.__name__, self.id, self.latitude,
                                                              self.longitude)


class Course(object):
    #   Constructeur de la classe Course
    #   Paramètres d'initialisation:
    #       - Id (généré par l'application)
    #       - Id de localisation GPS de l'adresse de "pick-up"
    #       - Id de localisation GPS de l'adresse destination
    #       - Nom du contact (obligatoire)
    #       - Numéro de téléphone principale (obligatoire)
    #       - Numéro de téléphone secondaire (facultatif)
    #       - Information de paiement (obligatoire?)
    #
    def __init__(self, id, time, from_location_id, to_location_id, contact_name, first_phone_no, second_phone_no,
                 payment_info):
        self.id = id
        self.time = time
        self.from_location_id = from_location_id
        self.to_location_id = to_location_id
        self.contact_name = contact_name
        self.first_phone_no = first_phone_no
        self.second_phone_no = second_phone_no
        self.payment_info = payment_info
        self.duration = self.calculateDuration()
        self.distance = self.calculateDistance()
        print(self)

    def calculateDuration(self):
        duration = "15"
        return duration

    def calculateDistance(self):
        duration = "15"
        return duration

    def __str__(self):
        return "{} id: {}, time: {}, from_location_id: {}, to_location_id: {}, contact_name: {}, first_phone_no: {}, second_phone_no: {}, payment_info: {}".format(
            self.__class__.__name__, self.id, self.time, self.from_location_id, self.to_location_id, self.contact_name,
            self.first_phone_no, self.second_phone_no, self.payment_info)


# Classe d'accès aux données GPS (locales ou distantes)
class DAO_Toolbox(object):
    def __init__(self, taxis_file, gps_locations_file, courses_list):
        self.taxis_file = taxis_file
        self.gps_locations_file = gps_locations_file
        self.taxi_list = self.loadTaxis(taxis_file)
        self.gps_locations_list = self.loadGPSLocations(gps_locations_file)
        self.gps_locations_count = len(self.gps_locations_list)
        self.gps_locations_list = []
        self.courses_list = self.loadCourses(courses_list)

    #
    # Création du planning de courses pour les taxis
    # Entrée: à définir
    # Sortie: nom de fichier output_file
    #
    # def createPlanning(self):
    #     output_file = open(os.path.join(chemin, output_file), "r")
    #     output_file = []
    #     taxis_list.append([ligne.split(";", 4) for ligne in output_file])
    #     taxis_file.close()
    #     taxi_object_list = []
    #     for taxi in taxis_list:
    #         id_taxi = taxi[0]
    #         nom = taxi[1]
    #         id_location = taxi[2]
    #         taxi_object = Taxi(id_taxi, nom, id_location)
    #         taxi_object_list.append(taxi_object)
    #     return taxi_object_list

    #
    # Chargement en mémoire du tableau d'objets Taxi
    # Entrée: nom de fichier
    #           Structure: "Id taxi";"Nom";"Id_Location"
    # Sortie: liste d'objets de type taxi
    #
    def loadCourses(self, courses_list):
        courses_object_list = []
        for course in courses_list:
            course_object = self.createCourse(courses_list.index(course), course)
            courses_object_list.append(course_object)
        return courses_object_list

    #
    # Chargement en mémoire du tableau d'objets Taxi
    # Entrée: nom de fichier
    #           Structure: "Id taxi";"Nom";"Id_Location"
    # Sortie: liste d'objets de type taxi
    #
    def loadTaxis(self, taxis_file):
        try:
            taxis_file = open(os.path.join(chemin, taxis_file), "r")
        except FileNotFoundError:
            print("Pas de fichier {} trouvé!".format(taxis_file.name))
            return None
        taxis_list = []
        taxis_list.append([ligne.split(";", 4) for ligne in taxis_file])
        taxis_file.close()
        taxi_object_list = []
        for taxi in taxis_list:
            id_taxi = taxi[0]
            nom = taxi[1]
            id_location = taxi[2]
            taxi_object = Taxi(id_taxi, nom, id_location)
            taxi_object_list.append(taxi_object)
        return taxi_object_list

    #
    # Chargement en mémoire du tableau d'objets Locations connues à partir du fichier des localisations gps.
    #   Les données GPS des adresses précédentes de ramassage ne sont pas conservées
    # Paramètres d'entrée: nom de fichier
    #           Structure: "Id_Location";"Adresse Postale";"Latitude";"Longitude";"Code secteur";"Type Location"
    # Paramètres de sortie: liste d'objets de type "Location"
    #
    def loadGPSLocations(self, gps_locations_file):
        try:
            gps_locations_file = open(os.path.join(chemin, gps_locations_file), "r")
        except IOError:
            print("Pas de fichier {} trouvé!".format(gps_locations_file.name))
            return None
        gps_locations_list = []
        gps_locations_list.append([ligne.split(";", 6) for ligne in gps_locations_file])
        gps_locations_file.close()
        gps_locations_object_list = []
        for gps_location in gps_locations_list:
            id_location = gps_location[0]
            postal_address = gps_location[1]
            latitude = gps_location[2]
            longitude = gps_location[3]
            sector_code = gps_location[4]
            location_type = gps_location[5]
            location_object = Location(id_location, postal_address, latitude, longitude, sector_code, location_type)
            gps_locations_object_list.append(location_object)
        return gps_locations_object_list


    #
    # Mise à jour des nouvelles localisations GPS à partir du fichier des positions gps connues.
    #   Les données GPS des adresses précédentes de ramassage ne sont pas conservées
    # Paramètres d'entrée: liste d'objets de type "Location"
    # Paramètres d'entrée: nom de fichier
    #           Structure: "Id_Location";"Adresse Postale";"Latitude";"Longitude";"Code secteur";"Type Location"
    #
    def updateGPSLocations(self):
        gps_locations_file = open(os.path.join(chemin, self.gps_locations_file), "a")
        gps_locations_newcount = len(self.gps_locations_list)
        start_index = self.gps_locations_count
        end_index = gps_locations_newcount
        if start_index == end_index:
            print("Pas de nouvelle localisation à écrire dans le fichier {}!", gps_locations_file.name)
        else:
            output_txt = ""
            for gpsloc in self.gps_locations_list[start_index:end_index]:
                gps_location_csv = "{};{};{};{};{};{}".format(gpsloc.id, gpsloc.postal_address, gpsloc.latitude, gpsloc.longitude, gpsloc.sector_code, gpsloc.location_type)
                output_txt += "{}\n".format(gps_location_csv)
            print("Ecriture du fichier {} - {} nouvelles localisations GPS créées".format(gps_locations_file.name, end_index-start_index))
            fichier.write(output_txt)
            fichier.close()

    #
    # Fonction MapBox de "forward geocoding" pour récupérer les coordonnées GPS d'une adresse donnée
    #   Se base sur des services commerciaux (mais gratuit pour 100.000 requêtes HTTP par mois)
    # https://docs.mapbox.com/api/search/#geocoding
    # Marche nickel, nécessite une clé API, 100.000 requêtes par mois (payant au delà!)
    # https://www.mapbox.com/pricing/#search
    #
    # Pour installer le package SDK: https://github.com/mapbox/mapbox-sdk-py
    #
    # Paramètres d'entrée: Adresse postale
    #           Structure: "Id_Location";"Adresse Postale";"Latitude";"Longitude";"Code secteur";"Type Location"
    # Paramètres de sortie: tableau indexé [latitude, longitude] ou code d'erreur HTTP si pas d'objet JSON retourné par l'API Mapbox
    #
    def getGPSLocation(self, postal_address):
        endpoint_full = "mapbox.places-permanent"  # utilisé pour des fonctions avancées payantes (on n'utilise pas!)
        endpoint = "mapbox.places"
        geocoder = Geocoder(access_token=MAPBOX_API_KEY)
        response = geocoder.forward(postal_address)
        first = response.geojson()['features'][0]
        if response.status_code == 200:
            return [round(coord, 5) for coord in first['geometry']['coordinates']]
        else:
            return response.status_code

    #
    # Retourne un "id_location"
    #   Si ID de localisation pas déjà enregistré localement, on va créér une nouvel ID et interroger la base Mapbox pour créér un nouvel objet Location et le rajouter à la liste gps_locations_list de la classe courante
    # Entrée: Adresse postale
    # Sortie: "id_location" ou "None" si l'API Mapbox n'a pas localisé l'adresse
    #
    def getLocationId(self, postal_address, location_type):
        for gps_location in self.gps_locations_list:
            pattern_pa = gps_location[1]
            if pattern_pa.match(postal_address):
                return gps_location[0]
            else:
                result = self.getGPSLocation(postal_address)
                if len(result) == 1:
                    print("Erreur de géolocalisation! Service Mapbox (code erreur HTTP {})".format(result))
                    return None
                else:
                    id_location = len(self.gps_locations_list)
                    latitude, longitude = result
                    location_object = Location(id_location, postal_address, latitude, longitude, None, location_type)
                    self.gps_locations_list.append(location_object)
                    return id_location

    # méthode de création d'un objet de type "Course" à partir de données d'entrées
    def createCourse(self, id_course, course):
        course = conversion_accents(course)
        course = re.sub(regex_special_chars, ' ', course)
        #print(course)
        # template = "09H20 - (POTEZ JUSTINE (ADO)) Saint-Laurent-du-Var - 591 Avenue Jean Aicard - RESIDENCE ST MARC BAT 7 - 06 73 80 48 45  - 06 25 18 28 24 PERE DEST Nice 2 Rue Raynardi / CPJA <<EXO OUI BT SERIE SI HOMME PRENDS COURSE, NE PAS PARLER A JUSTINE"
        tab_1 = course.split("<<")
        #print(tab_1)
        # payment info -> EXO OUI BT SERIE SI HOMME PRENDS COURSE, NE PAS PARLER A JUSTINE"
        payment_info = tab_1[1].strip()
        #print("PROUT", payment_info)
        #payment_info = tab_1
        # tab_2 -> template = "09H20 - (POTEZ JUSTINE (ADO)) Saint-Laurent-du-Var - 591 Avenue Jean Aicard - RESIDENCE ST MARC BAT 7 - 06 73 80 48 45  - 06 25 18 28 24 PERE DEST Nice 2 Rue Raynardi / CPJA
        tab_2 = tab_1[0]
        tab_3 = tab_2.split(" DEST ")
        # Extraction adresse destination de la course
        # tab_4 -> template = "Nice 2 Rue Raynardi / CPJA "
        # tab_4 -> template = "S20 Nice  CYCLOTRON - CAL - 227 Avenue de la Lanterne "
        tab_4 = tab_3[1]
        tab_4_tmp = tab_4.split(" ")
        is_sector_code = True if re.match(regex_code_secteur, tab_4_tmp[0]) else False
        sector_code = tab_4_tmp[0].strip() if is_sector_code else ""
        to_city = tab_4_tmp[1] if is_sector_code else tab_4_tmp[0]
        to_street = " ".join(tab_4_tmp[2:len(tab_4_tmp)]).strip() if sector_code else " ".join(tab_4_tmp[1:len(tab_4_tmp)])
        to_postal_address = to_street.strip() + " " + to_city.strip()

        # Extraction informations client, heure et adresse de ramassage
        # tab_5 -> template = "09H20 - (POTEZ JUSTINE (ADO)) Saint-Laurent-du-Var - 591 Avenue Jean Aicard - RESIDENCE ST MARC BAT 7 - 06 73 80 48 45  - 06 25 18 28 24 PERE
        # tab_5 -> template = "09H15 - (ROBBE CLAUDE) NICE - 12 RUE DES PONCHETTES - MAISON EN FACE DE L ARCHE- PRES DU COURS SALEYA - 06 82 56 88 06 - 04 93 13 08 28  "
        tab_5 = tab_3[0]
        tab_6 = tab_5.split(" - ")
        #print("Phone 1", tab_6)
        time = tab_6[0].strip()
        # Nom contact et ville
        # template = "(POTEZ JUSTINE (ADO)) Saint-Laurent-du-Var "
        tab_field_2 = tab_6[1].strip()
        tab_field_2_tmp = tab_field_2.strip().split(" ")
        from_city = tab_field_2_tmp[-1]
        contact_name_tmp = " ".join(tab_field_2_tmp[0:len(tab_field_2_tmp) - 1])
        contact_name = contact_name_tmp[1:len(contact_name_tmp) - 1].strip()
        # Adresse et complément d'adresse
        from_street = tab_6[2]
        from_postal_address = from_street.strip() + " " + from_city.strip()
        # Numéros de tél de contact
        phone_list = []
        #print("Phone", tab_6)
        for field in tab_6:
            if re.match(regex_phone_number, field):
                phone_number = re.sub('[a-zA-Z]', '', field)
                phone_list.append(phone_number)
        first_phone_no = phone_list[0]
        second_phone_no = phone_list[1] if len(phone_list) == 2 else ""
        position_fin_adresse = len(tab_6) - len(phone_list)
        from_address_info = " - ".join(tab_6[3:position_fin_adresse])

        from_location_id = self.getLocationId(from_postal_address, 'D')
        to_location_id = self.getLocationId(to_postal_address, 'D')
        course_Object = Course(id_course, time, from_location_id, to_location_id, contact_name, first_phone_no, second_phone_no, payment_info)

        return course_Object


#########################################################################################################################################################################################################################################
#
#   Début du programme principal
#
#   Etapes:
#       1 - (Non utilisé dans l'algorithme) Chargement en mémoire du tableau d'objets Taxi (à partir du fichier "taxi_locations_file")
#       2 - Chargement en mémoire du tableau d'objets Locations connues (principalement les destinations) et adresses associées  (à partir du fichier "course_locations_file"). On ne stocke pas les adresses de ramassage des clients
#       3 - Reformatage des données d'entrée (fournies par les établissement de santé) et enregistrement dans un tableau d'objets structurés (dans l'éventualité d'un stockage dans une base de données): Courses et Locations
#       4 - Pour chaque feuille de route (course), on va calculer la distance et durée
#       5 - Algorithme pour les affectations des courses aux taxis disponible (on ne prend pas en compte le lieu de départ du taxi) mais seulement les enchaînements de course
#       6 - Ecriture du nouveau planning dans un fichier text "Planning.csv"
#       7 - Mise à jour des nouvelles destinations dans le fichier "course_locations_file"
#
########################################################################################################################################################################################################################################

#
# Chargement des informations de courses dans notre base d'objets locaux
#
# Lecture du fichier d'entrée (EML) - fichier binaire de messagerie à décrypter et vérifier le type d'encodage de caractères
file = open(os.path.join(chemin, input_file), "rb")
msg = BytesParser(policy=policy.default).parse(file)
# texte_courses = msg.get_body(preferencelist=("plain")).get_content() # version qui semble marcher aussi donc pas de nécessité d'utiliser les fonctions codées localement get_charset() et get_body()
texte_courses = get_body(msg)
#print(texte_courses)
# Extraction des données utiles à partir du délimiteur >>
# Enregistrement des données dans un tableau indexé "courses_tab" non structuré
patron = re.compile(regex_dsup_delimiter)
courses_tab = patron.split(texte_courses)

# Suppression du libellé Taxi Médical à la fin
# ces 2 ligne marchaient au tout début... pas chercher à comprendre :-D
# libelle_societe = [course for course in courses_tab if re.match(regex_libelle_societe, course)][0]
# courses_tab.remove(libelle_societe)
courses_tab.remove(courses_tab[-1])
nombre_courses = len(courses_tab)
print("Nombre courses: {}".format(nombre_courses))
liste_Courses = []
#
# for course in courses_tab:
#     print(course)

# Création de l'objet DAO pour charger la structure de données en mémoire
DAO_Toolbox = DAO_Toolbox(taxis_file, gps_locations_file, courses_tab)

courses = DAO_Toolbox.courses_list
gps_locations = DAO_Toolbox.gps_locations_list

#
#   Début de l'algorithme (pour l'instant rien du tout :-DD)
#

# Ecriture du fichier de sortie ( A implémenter )
output_txt = ""
for course in courses_tab:
    course = conversion_accents(course)
    output_txt += "{}\n".format(re.sub(regex_special_chars, ' ', course))
fichier = open(os.path.join(chemin, output_file), "w")
print("Ecriture du fichier {} - {} nouvelles courses créées".format(fichier.name, nombre_courses))
fichier.write(output_txt)
fichier.close()

# Enregistrement des nouvelles destinations
DAO_Toolbox.updateGPSLocations()
