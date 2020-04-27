import math

class Point(object):
    def __init__(self, longitude, latitude, lieu_dit):
        self.longitude = float(longitude)
        self.latitude = float(latitude)
        self.lieu_dit = lieu_dit
        #print(float(self.longitude), float(self.latitude))

    def calculateDistanceVolOiseau(self, other):
        earth_radius = 6371
        longA = (math.pi / 180) * self.longitude
        latA = (math.pi / 180) * self.latitude
        longB = (math.pi / 180) * other.longitude
        latB = (math.pi / 180) * other.latitude
        X = (longB - longA) * math.cos(((latA + latB) / 2))
        Y = latB - latA
        D = math.sqrt(X * X + Y * Y) * earth_radius
        return D

A = Point(43.696342, 7.174842, "Montaleigne")
B = Point(43.687953, 7.173538, "Chemin des Mauberts")
C = Point(43.676365, 7.175073, "Garage Melani")
D = Point(43.683708, 7.179375, "Domicile")

for point in list([A,B,C]):
    distance = D.calculateDistanceVolOiseau(point)
    print("Distance vol d'oiseau {} -> {} = {:0.2f} km".format(D.lieu_dit, point.lieu_dit,distance))

