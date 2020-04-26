import sys
import math
import email
import re
#import io
from email import policy
from email.parser import BytesParser

s = "Salut \n Comment ca va ?"
t = "08H15 - (TOYA  IDA) NICE - 16 RUE ACCHIARDI DE SAINT LEGER - 06 67 81 10 54 \
DEST S31 NICE 8 AVENUE MALAUSSENA - DCT BRENET <<EXO OUI \
BT AU RETOUR \
AP>> 15"

regex = re.compile(r'[\n\r\t]')
s = regex.sub(" ", s)
#t = regex.sub(" ", t)

#print(s)
#print(t)

file = open("C:\\Users\\User\\Downloads\\Mail des resas.eml", "r")

# # Affichage à l'écran du fichier eml brut (header et body en html...
# lines = file.readlines()
# #file.close()
# for line in lines:
#     print(line.strip())

#
# Début du traitement
#
# Lecture du fichier d'entrée (EML)
file = open("C:\\Users\\User\\Downloads\\Mail des resas.eml", "rb")
msg = BytesParser(policy=policy.default).parse(file)
text = msg.get_body(preferencelist=("plain")).get_content()
#print(text)

regex_coursesold = r"[0-9]{1,2}H[0-9]{1,2} - .*>> [0-9]{1,2}"
regex_courses = "[0-9]{1,2}H[0-9]{1,2} - .*>>"
regex_dsup = '>>'
regex_nice = r'NICE'
regex_cr_lf = '[\n\r]'

regex = re.compile(regex_cr_lf)
texte = regex.sub(" ",text)

print(texte)
patron = re.compile(regex_dsup)
resultat = patron.split(texte)
patron2 = re.compile(regex_courses)
resultat2 = patron2.split(texte)
print ("patron :",patron,"résultat : ",resultat)
print ("patron :",patron,"Nombre courses:",len(resultat))
print ("patron :",patron,"Nombre courses:",len(resultat2))

# if resultat :
#  print (resultat.start(), resultat.end())
# else:
#  print (resultat)

motif = ">>"
valuePart = text.split(motif)
#print(valuePart)


#if re.match(regex_courses, text):
 #   line = regex_cr_lf.sub("", text)

# Ecriture du fichier de sortie
fichier = open("C:\\Users\\User\\Downloads\\data.txt", "a")
fichier.write(text)
fichier.close()

file.close()


# Write an answer using print
# To debug: print("Debug messages...", file=sys.stderr)
