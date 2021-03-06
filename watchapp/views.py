from django.http import HttpResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, redirect, render_to_response
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages 
from django.contrib.auth.models import User, Group
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from forms import SignUpForm
from watchapp.models import ConstructorCompany, Property, UserProfile, Sensor, Event
from watchapp.serializers import EventSerializer
from rest_framework import viewsets
import logging
from django.views.decorators.csrf import csrf_exempt
import json
import ho.pisa as pisa
import cStringIO as StringIO
import cgi
from django.template import RequestContext
from django.template.loader import render_to_string
import logging
import sys
import datetime
from django.core import serializers
import csv
from forms import ProfileForm
from django.core.mail import send_mail

log = logging.getLogger(__name__)

####################### Vistas index o para autenticacion #######################

def index(request):
	"""
	Esta vista es la pagina principal de WatchApp.
		@param request
		@author Lorena Salamanca
	"""
	return HttpResponse("Hello, world. You're at the watchapp index.")

def signup(request):
    """
    Esta funcion contiene el formulario de creacion de usuarios para WatchApp
    	@param request
    	@author Lorena Salamanca
    """
    if request.method == 'POST':  # If the form has been submitted...
        form = SignUpForm(request.POST)  # A form bound to the POST data
        if form.is_valid():  # All validation rules pass
 
            # Process the data in form.cleaned_data
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            email = form.cleaned_data["email"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
 
            # At this point, user is a User object that has already been saved
            # to the database. You can continue to change its attributes
            # if you want to change other fields.
            user = User.objects.create_user(username, email, password)
            user.first_name = first_name
            user.last_name = last_name
 
            # Save new user attributes
            user.save()
            return HttpResponseRedirect(reverse('watchapp:login'))  # Redirect after POST
    else:
        form = SignUpForm()
 
    data = {
        'form': form,
    }
    return render_to_response('watchapp/signup.html', data, context_instance=RequestContext(request))

def login_success(request):
    """
    Esta funcion redirecciona al home de constructoras o de usuarios (propietarios / residentes)
    dependiendo del Group al que pertenezca el usuario autenticado.
    	@param request
    	@author Lorena Salamanca
    """    
    if request.user.groups.filter(name="constructoras").exists():        
        return HttpResponseRedirect(reverse('watchapp:constructora_home'))
    elif request.user.groups.filter(name="usuarios").exists():       
        return HttpResponseRedirect(reverse('watchapp:users_home'))


@login_required()
def sensor_configuration(request):
    """
    Esta funcion tiene el contenido del home de usuarios (propietarios / residentes), 
    se puede acceder despues de la autenticacion de un usuario que este en el Group usuarios
    	@param request
    	@author Lorena Salamanca
    """
    if request.method == 'POST':
        sensors = []
	selected_property = Property.objects.get(name=request.POST["select_as_owner"])
	log.debug("Id Propiedad: " + str(selected_property.id))
	sensors = property_sensors(request,selected_property.id) 
        return render(request, 'watchapp/sensor_configuration.html', {
        "selected_property": selected_property,
        "request": request,
        "Sensors":sensors,
        })
    else:
        return render(request, 'watchapp/sensor_configuration.html', {
            "request": request,
        })


####################### Vistas para crear un sensor en un plano #######################

@login_required()
@csrf_exempt
def set_position_ajax(request):
        response_data = {}
	data = json.loads(request.body) 
        sensors = []
        selected_property = Property.objects.get(name=data['property'])
        sensor = Sensor(
		code = data['code'],
		description = data['description'],
		type =  data['type'],
		location_in_plan = data['location_in_plan'],
		is_discrete = data['location_in_plan'],
		property = selected_property,
		value = '0'
        )
        sensor.save()
	sensorUpdate=Sensor.objects.get(pk=sensor.pk)
        typeSensor =data['code']
        sensorUpdate.code = typeSensor[0]+'-'+str(sensor.pk);       
	sensorUpdate.save()
	sensors = property_sensors(request,selected_property.id) 
	print 'Add ok'
        data = {}
        data["sensor_id"] = sensorUpdate.id
        data["code"] = sensorUpdate.code
        data["location_in_plan"] = sensorUpdate.location_in_plan
        data["description"] = sensorUpdate.description
        data["type"] = sensorUpdate.type
        return HttpResponse(
                json.dumps(data),
                content_type="application/json"
            )


####################### Vistas para borrar un sensor en un plano #######################

@login_required()
@csrf_exempt
def delete_position_ajax(request):
        response_data = {}
	data = json.loads(request.body) 
        selected_property = Property.objects.get(name=data['property'])
	sensorUpdate=Sensor.objects.get(location_in_plan = data['location_in_plan'], property = selected_property)
	sensorUpdate.delete()
        response_data['msg'] = 'ok'
        return HttpResponse(
                json.dumps(data),
                content_type="application/json"
            )

####################### Vistas para propietarios / residentes #######################

@login_required()
@user_passes_test(lambda u: u.groups.filter(name='usuarios').exists(), login_url='/watchapp/login/')
def users_home(request):
    """
    Esta funcion tiene el contenido del home de usuarios (propietarios / residentes), 
    se puede acceder despues de la autenticacion de un usuario que este en el Group usuarios
    	@param request
    	@author Lorena Salamanca
    """
    if request.method == 'POST':
        sensors = []
        selected_property = ''
        asresident = 0;
        if request.POST.get('select_as_owner', '') == "0":
            selected_property = Property.objects.get(name=request.POST.get('select_as_resident', ''))
            sensors = property_sensors(request,selected_property.id)
            asresident = 1;
        elif request.POST.get('select_as_resident', '') == "0":
            selected_property = Property.objects.get(name=request.POST.get('select_as_owner', ''))
            log.debug("Id Propiedad: " + str(selected_property.id))
            sensors = property_sensors(request,selected_property.id)
        return render(request, 'watchapp/users_home.html', {
        "selected_property": selected_property,
        "asresident":asresident,
        "request": request,
        "Sensors":sensors,
        })
    else:
        return render(request, 'watchapp/users_home.html', {
            "request": request,
        })

@login_required()
@user_passes_test(lambda u: u.groups.filter(name='usuarios').exists(), login_url='/watchapp/login/')
def change_secure_mode(request, property_id, asresident):
    """
    Esta funcion activa / desactiva el modo seguro de un inmueble
        @param request
        @author Lorena Salamanca
    """
    if request.method == 'GET':
        selected_property = Property.objects.get(pk=property_id)
        if request.GET.get('change_secure_mode_checkbox', ''):
            selected_property.is_secure_mode = True
            selected_property.save()
        else:
            selected_property.is_secure_mode = False
            selected_property.save()
        sensors = property_sensors(request,selected_property.id)
        log.debug("change_secure_mode: Sensor secure mode val: " + str(selected_property.is_secure_mode))
        log.debug("change_secure_mode: asresident val: " + str(asresident))
        return render(request, 'watchapp/users_home.html', {
        "selected_property": selected_property,
        "request": request,
        "Sensors":sensors,
        "asresident":asresident,
        })

@login_required()
def render_sensor_status(request):
    """
    Esta funcion permite mostrar los datos que se mostraran en la pagina sensorstatus
        @param request
        @author German Bernal
    """      
    propertyList = propertys_by_User(request)    
    if request.method == 'POST':
        sensors = property_sensors(request,request.POST["select_Property"])        
        return render(request,"watchapp/sensorstatus.html",{
                "Sensors":sensors,
                "propertyList":propertyList
            })
    else:
        return render(request,"watchapp/sensorstatus.html",{
               "propertyList":propertyList
            })   
     
@login_required()
def property_sensors(request,property_id):
    """
    Esta funcion permite obtener los sensores por propiedad,
        @param request
        @author German Bernal
    """
    log.debug("property_sensors: val: " + str(property_id))
    sensors = Sensor.objects.filter(property_id=property_id)
    return sensors

@login_required()
def propertys_by_User(request):
    """
    Esta funcion permite obtener las propiedad por usuario.
        @param request
        @author German Bernal
    """    
    propertyList = []
    user = User.objects.filter(username=request.user.username)
    userP = UserProfile.objects.get(user_id=user[0].id)
    for p in userP.properties_as_resident.all():
        property = Property.objects.get(pk=p.id)
        if property not in propertyList:
            propertyList.append(property)
    for p in userP.properties_as_owner.all():
        property = Property.objects.get(pk=p.id)
        if property not in propertyList:
            propertyList.append(property)
    return propertyList

@login_required()
def update_sensor(request):
    """
    Esta funcion permite actualizar el valor discreto y continuo de un sensor en la base de datos,
        @param request
        @author German Bernal
    """
    log.debug("update_sensor: val: " + "Entro a update_sensor")
    if request.method == 'GET':
        sensor_id = request.GET['sensor_id']
        log.debug("update_sensor: Sensor val: " + str(sensor_id))
        value = request.GET['value']
        log.debug("update_sensor: value val: " + str(value))
        sensor = Sensor.objects.get(pk=sensor_id)
        sensor.value = value
        sensor.save()
        data = {}
        data["sensor_id"] = sensor.id
        data["code"] = sensor.code
        data["location_in_plan"] = sensor.location_in_plan
        data["value"] = sensor.value
        data["valueDisplay"] = sensor.get_value_display()
        log.debug("update_sensor: value val: " + str(data))
        return HttpResponse(
                json.dumps(data),
                content_type="application/json"
            )


@login_required()
def update_value(request, property_id, asresident):
    """
    Esta funcion permite actualizar el valor discreto y continuo de un sensor en el template,
        @param request
        @author German Bernal
    """
    log.debug("update_value: val: " + "Entro a update_value")
    log.debug("update_value: Property val: " + str(property_id))
    log.debug("update_value: asresident val: " + str(asresident))
    if request.method == 'GET':
        selected_property = Property.objects.get(pk=property_id)
        sensors = property_sensors(request,selected_property.id)
        return render(request, 'watchapp/users_home.html', {
        "selected_property": selected_property,
        "asresident":asresident,
        "request": request,
        "Sensors":sensors,
        })

####################### Vista para rest_framework #######################

class EventViewSet(viewsets.ModelViewSet):
   """
   Esta funcion es el API endpoint que permite hacer peticiones GET / POST a eventos.
	     @param viewsets
		 @author Lorena Salamanca
   """
   queryset = Event.objects.all()
   serializer_class = EventSerializer

####################### Inicio Vistas para el reporte de los eventos del inmueble del propietario #######################

@login_required()
@user_passes_test(lambda u: u.groups.filter(name='usuarios').exists(), login_url='/watchapp/login/')
def rpt_owner_property(request):
    """
    Vista Para inicializar la pagina del reporte de eventos del propietarioa
    	@param request
    	@author Ricardo Restrepo
    """    
    if request.user.groups.filter(name="usuarios").exists():        
        return render(request, 'watchapp/rpt_owner_property.html', { "request": request, })
    elif request.user.groups.filter(name="constructoras").exists():       
        return HttpResponse("No tiene permisos de acceso.")

def generate_pdf(html):
    """
    Funcion para generar el archivo PDF y devolverlo mediante HttpResponse
    	@param request
    	@author Ricardo Restrepo
    """ 
    result = StringIO.StringIO()
    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('Error al generar el PDF: %s' % cgi.escape(html))

@login_required()
@csrf_exempt
def get_report_owner_property(request):
    """
    Funcion para crear el archivo generar el pdf del reporte de eventos del propietario
	Requisitos:
	http://django.es/blog/generar-pdfs-con-django-y-pisa/
	easy_install pisa
        sudo pip install html5lib
        sudo pip install pyPDF
    	@param request
    	@author Ricardo Restrepo
    """   
    # Array de eventos
    events = []
    #Parametros json enviados por ajax
    data = json.loads(request.body) 
    print data['dateInit']
    pData=""

    if data['property']=='0':
        # Consultamos todos los inmuebles de un propietario
        properties = request.user.userprofile.properties_as_owner.all()
        # Consultamos todos los eventos de todos los inmuebles de un propietario
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']])
        pData="Todas"
    else:
        # Consultamos la propiedad
        selected_property = Property.objects.get(name=data['property'])  
        pData=data['property']
        # Consultamos los eventos de la propiedad
        events = Event.objects.filter(property_id=selected_property.id,date__range=[data['dateInit'], data['dateFinal']])


    if(len(events)==0): return HttpResponse("0")

    # Recuperamos el html del template del reporte
    html = render_to_string('watchapp/template_rpt_owner_property.html', {'pagesize':'A4', 'Events':events, 'property':str(pData), 'dateInit':str(data['dateInit']).split(' ')[0],'dateFinal':str(data['dateFinal']).split(' ')[0] }, context_instance=RequestContext(request))
    # Convertimos el html  a pdf    
    return generate_pdf(html)

class PisaHandler(logging.Handler):
    """
    Funcion para controlar excepciones de la libreria de PISA PDF
    	@param request
    	@author Ricardo Restrepo
    """  
    def emit(self, record):
        print >> sys.stderr, record

logging.getLogger("ho.pisa").addHandler(PisaHandler())

@login_required()
@csrf_exempt
def get_event_owner_property(request):
    """
    Funcion para consultar los de eventos inmueble del propietario
    	@param request
    	@author Ricardo Restrepo
    """   
    # Array de eventos
    events = []
    #Parametros json enviados por ajax
    data = json.loads(request.body) 
    print data
    if data['property']=='0':
        # Consultamos todos los inmuebles de un propietario
        properties = request.user.userprofile.properties_as_owner.all()
        # Consultamos todos los eventos de todos los inmuebles de un propietario
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']])
    else:
        # Consultamos la propiedad
        selected_property = Property.objects.get(name=data['property'])  
        # Consultamos los eventos de la propiedad
        events = Event.objects.filter(property_id=selected_property.id,date__range=[data['dateInit'], data['dateFinal']])

    if(len(events)==0): 
        return HttpResponse("0")
    else:
	# Collecion de eventos
	dataEvents=[]
	# Recorremos todos los eventos
	for e in events:
                dataE = {}	
		dataE["date"] = str(e.date.date())
		dataE["description"] = str(e.description.encode('utf8'))
		dataE["type"] = str(e.get_type_display())
		if (e.is_critical): 
		     dataE["is_critical"] = "Si" 
		else: 
		     dataE["is_critical"] ="No"
		if (e.is_fatal): 
		     dataE["is_fatal"] = "Si" 
		else: 
		     dataE["is_fatal"] = "No"
		dataE["property"] = e.property.name.encode('utf8')
		dataE["sensor"] = str(e.sensor.description.encode('utf8'))
		# Agregamos el evento a la coleccion
		dataEvents.append(dataE)
	# Retornamos los eventos en formato JSON
        return HttpResponse(
                json.dumps(dataEvents),
                content_type="application/json"
            )
####################### Fin Vistas para el reporte de los eventos del inmueble del propietario #######################


@login_required()
def get_owner_reports(request):
    """
    Esta funcion muestra las propiedades del usuario autenticado y le 
    permite generar reportes de los eventos de sus inmuebles
        @param request
        @author Lorena Salamanca
    """
    if request.method == 'POST':
        sensors = []
        selected_property = Property.objects.get(name=request.POST["select_as_owner"])
        log.debug("Id Propiedad: " + str(selected_property.id))
        events = selected_property.event_set.all() 
        return render(request, 'watchapp/get_owner_reports.html', {
        "selected_property": selected_property,
        "request": request,
        "events":events,
        })
    else:
        return render(request, 'watchapp/get_owner_reports.html', {
            "request": request,
        })

####################### Vistas para constructoras #######################

@login_required()
@user_passes_test(lambda u: u.groups.filter(name='constructoras').exists(), login_url='/watchapp/login/')
def constructora_home(request):
    """
    Esta funcion tiene el contenido del home de constructoras, 
    se puede acceder despues de la autenticacion de un usuario que este en el Group constructoras
    	@param request
    	@author Lorena Salamanca
    """
    return render(request, 'watchapp/constructora_home.html', {
        "request": request,
    })

@login_required()
@user_passes_test(lambda u: u.groups.filter(name='constructoras').exists(), login_url='/watchapp/login/')
def rpt_admin_all_property(request):
    """
    Vista temporal mockups
        @param request
        @author Ricardo Restrepo
    """        
    return render(request, 'watchapp/rpt_admin_all_property.html', { "request": request, })


@login_required()
@user_passes_test(lambda u: u.groups.filter(name='constructoras').exists(), login_url='/watchapp/login/')
def admin_file_upload(request):
    """
    Vista temporal mockups
        @param request
        @author Ricardo Restrepo
    """ 
    log.debug("admin_file_upload: entro!! ")
    if request.user.groups.filter(name="constructoras").exists():
        return render(request, 'watchapp/admin_file_upload.html', { "request": request, })
    elif request.user.groups.filter(name="usuarios").exists():       
        return HttpResponse("No tiene permisos de acceso.")

@login_required()
@user_passes_test(lambda u: u.groups.filter(name='constructoras').exists(), login_url='/watchapp/login/')
def process_file(request):
    """
    Esta funcion procesa el archivo que contiene las propiedades a configurar
        @param request
        @author German Bernal
    """ 
    response_data = {}
    response_data["valid"] = True;
    try:
        log.debug("process_file: entro!! ")
        if request.user.groups.filter(name="constructoras").exists():
            #return HttpResponse("Entro a la funcion.")
            log.debug("process_file: entro if ")
            log.debug("process_file: entro if: Request: " + str(request))
            log.debug("process_file: entro if: Files " + str(request.FILES))
            for key in request.FILES:
                log.debug("process_file: file: " + key)
                log.debug('process_file: Structure is Valid: ' + str(validate_data_structure(request.FILES[key],4)))
                row_count = sum(1 for row in request.FILES[key])
                valid_structure = validate_data_structure(request.FILES[key],5)
                isvalid = True if row_count > 0 and valid_structure else False
                if isvalid:
                    res = uploadres = upload_propertys(request.FILES[key])
                    if res["upload_status"] == "failed":
                        response_data["valid"] = False;
                    response_data["message"] = res["message"]
                else:
                    response_data["valid"] = False;
                    if not valid_structure > 0:
                        response_data["message"] = "El archivo tiene una estructura no valida!!"
                    elif not row_count > 0:
                        response_data["message"] = "El archivo no tiene datos"
                    break
            return HttpResponse(
                    json.dumps(response_data),
                    content_type="application/json"
                )
        elif request.user.groups.filter(name="usuarios").exists():       
            return HttpResponse("No tiene permisos de acceso.")
    except Exception as inst:
        log.debug("process_file: error: " + str(inst))
        response_data["message"] = str(inst)
        response_data["valid"] = False;
        return HttpResponse(
                json.dumps(response_data),
                    content_type="application/json"
                )


def upload_propertys(file):
    """
    Esta funcion crea las propiedades de un archivo
        @param request
        @author German Bernal
    """ 
    result = {}
    property_inserted = False
    property_exists = False
    reader = csv.reader(file, delimiter = ',')
    for row in reader:
        log.debug("upload_propertys: row: " + str(row))
        log.debug("upload_propertys: row - len: " + str(len(row)))
        prop = Property.objects.filter(name = row[0].strip(),address = row[1].strip(), fixed_phone = row[2].strip(),plan =row[3].strip())
        log.debug("upload_propertys: prop count: " + str(len(prop)))
        if len(prop) == 0:
            user = User.objects.filter(username=row[4].strip())
            if len(user) > 0: 
                property = Property(name = row[0].strip(),address = row[1].strip(), fixed_phone = row[2].strip(),plan =row[3].strip())
                property.save()
                userP = UserProfile.objects.get(user_id=user[0].id)
                userP.properties_as_owner.add(property);
                property_inserted = True
        else:
            property_exists = True
    file.close()
    if property_inserted and not property_exists:
        result["upload_status"] = "complete";
        result["message"] = "Propiedades registradas.";
    elif property_inserted and property_exists:
        result["upload_status"] = "partial";
        result["message"] = "Carga Parcial. Algunas de las propiedades ya estan registradas o el propietario no existe";
    else:
        result["upload_status"] = "failed";
        result["message"] = "Las propiedades ya estan registradas en el sistema o los propietarios no estan registrados";
    return result

def validate_data_structure(file,col_count):
    """
    Esta funcion valida la estructura de un archivo
        @param request
        @author German Bernal
    """ 
    isvalid = True
    reader = csv.reader(file, delimiter = ',')
    for row in reader:
        log.debug("validate_structure_data: row: " + str(row))
        log.debug("validate_structure_data: row count: " + str(len(row)))
        if len(row) < col_count:
            isvalid = False
            break
    return isvalid


####################### Reportes para Constructora #######################
		
@login_required()
@user_passes_test(lambda u: u.groups.filter(name='constructoras').exists(), login_url='/watchapp/login/')
@csrf_exempt
def get_report_admin_all_property(request):
    """
    Funcion que consulta los eventos de la constructora y genera el pdf 
    	@param request
    	@author Lorena Salamanca
    """   
    # Array de eventos
    events = []
    #Parametros json enviados por ajax
    data = json.loads(request.body) 
    pData=""

    # Consultamos todos los inmuebles de un propietario
    constructora = ConstructorCompany.objects.get(user_id=request.user.userprofile.id)
    properties = Property.objects.filter(constructor_company_id=constructora.id)
    print data['event_type']
    if data['event_type']=='-1':
        # Consultamos todos los eventos de todos los inmuebles de un propietario
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']])
        pData="Todos"
    else:
        # Consultamos la propiedad
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']], type=data['event_type'])
        pData=data['event_type']
        if data['event_type']=='0': pData = 'Disparo de alarma'
        if data['event_type']=='1': pData = 'Activar alarma'
        if data['event_type']=='2': pData = 'Desactivar alarma'
        if data['event_type']=='3': pData = 'Alerta en sensor'
        if data['event_type']=='4': pData = 'Cambio actuador'
	
    if(len(events)==0): return HttpResponse("0")
    # Collecion de eventos
    dataEvents=[]
    # Recorremos todos los eventos
    for e in events:
        dataE = {}	
        dataE["date"] = str(e.date.date())
        dataE["type"] = str(e.get_type_display())
        dataE["description"] = str(e.description.encode('utf8'))
        if (e.is_critical): 
        	dataE["is_critical"] = "Si" 
        else: 
        	dataE["is_critical"] ="No"
        if (e.is_fatal): 
        	dataE["is_fatal"] = "Si" 
        else: 
        	dataE["is_fatal"] = "No"
        dataE["property"] = e.property.name.encode('utf8')
        dataE["sensor"] = str(e.sensor.description.encode('utf8'))
        dataE["propietario"] = str(e.property.properties_as_owner.all()[0].user.first_name.encode('utf8')) + ' ' + str(e.property.properties_as_owner.all()[0].user.last_name.encode('utf8'))
        # Agregamos el evento a la coleccion
        dataEvents.append(dataE)
    # Recuperamos el html del template del reporte
    print dataEvents
    print 'pdata' + pData
    html = render_to_string('watchapp/template_rpt_admin_all_property.html', {'pagesize':'A4', 'sdf':dataEvents, 'event_type':str(pData), 'dateInit':str(data['dateInit']).split(' ')[0],'dateFinal':str(data['dateFinal']).split(' ')[0] }, context_instance=RequestContext(request))
    # Convertimos el html  a pdf    
    return generate_pdf(html)
	
@login_required()
@user_passes_test(lambda u: u.groups.filter(name='constructoras').exists(), login_url='/watchapp/login/')
@csrf_exempt
def get_event_admin_all_property(request):
    """
    Funcion que consulta los eventos de la constructora y mostrarlos en pantalla
    	@param request
    	@author Ricardo Restrepo
    """   
    # Array de eventos
    events = []
    #Parametros json enviados por ajax
    data = json.loads(request.body) 
    constructora = ConstructorCompany.objects.get(user_id=request.user.userprofile.id)
    properties = Property.objects.filter(constructor_company_id=constructora.id)
    print data['event_type']
    if data['event_type']=='-1':
        # Consultamos todos los eventos de todos los inmuebles de un propietario
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']])
    else:
        # Consultamos la propiedad
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']], type=data['event_type'])

    if(len(events)==0): 
        return HttpResponse("0")
    else:
	# Collecion de eventos
	dataEvents=[]
	# Recorremos todos los eventos
	for e in events:
		dataE = {}	
		dataE["date"] = str(e.date.date())
		dataE["type"] = str(e.get_type_display())
		dataE["description"] = str(e.description.encode('utf8'))
		if (e.is_critical): 
		     dataE["is_critical"] = "Si" 
		else: 
		     dataE["is_critical"] ="No"
		if (e.is_fatal): 
		     dataE["is_fatal"] = "Si" 
		else: 
		     dataE["is_fatal"] = "No"
		dataE["property"] = e.property.name.encode('utf8')
		dataE["sensor"] = str(e.sensor.description.encode('utf8'))
		dataE["propietario"] = str(e.property.properties_as_owner.all()[0].user.first_name.encode('utf8')) + ' ' + str(e.property.properties_as_owner.all()[0].user.last_name.encode('utf8'))
		# Agregamos el evento a la coleccion
		dataEvents.append(dataE)
	# Retornamos los eventos en formato JSON
        return HttpResponse(
                json.dumps(dataEvents),
                content_type="application/json"
            )

@login_required()
@user_passes_test(lambda u: u.groups.filter(name='usuarios').exists(), login_url='/watchapp/login/')
def update_profile(request):
    """
    Vista temporal mockups
    	@param request
    	@author Fredy Wilches
    """    
    user = User.objects.filter(username=request.user.username)
    userP = UserProfile.objects.get(user_id=user[0].id)

    if request.method == 'POST':
	form=ProfileForm(request.POST, request.FILES)
	if form.is_valid():
		userP.mobile_number=form.cleaned_data['mobile_number']
		u=user[0]
		u.email=form.cleaned_data['email']
		u.set_password(form.cleaned_data['password'])
		f=request.FILES['file']
		#print(f)
		with open('smarthome/static/images/'+f.name, 'wb+') as destination:
			for chunk in f.chunks():
				destination.write(chunk)
		userP.photo=f.name
		userP.save()
		u.save()
		#send_mail('Usuario Actualizado', 'Datos nuevos<p>'+'test', 'fredy.wilches@gmail.com', [user[0].email], False, 'fredy.wilches@gmail.com', 'pwd')
		return render(request, 'watchapp/update_profile.html', { "request": request, "form": form, "actualizado":True})	
    else:
	data = {'mobile_number' : userP.mobile_number,
		'email' : user[0].email}
	form=ProfileForm(data)

	return render(request, 'watchapp/update_profile.html', { "form": form, "actualizado":False})


    if request.user.groups.filter(name="usuarios").exists():        
        return render(request, 'watchapp/update_profile.html', { "request": request, "form": form, "actualizado":False})
    elif request.user.groups.filter(name="constructoras").exists():       
        return HttpResponse("No tiene permisos de acceso.")


####################### Reporte Todos los eventos de la constructora por propietario #######################

@login_required()
@user_passes_test(lambda u: u.groups.filter(name='constructoras').exists(), login_url='/watchapp/login/')
def rpt_admin_all_property_by_owner(request):
    """
    Vista reporte todos los eventos de la constructora por propietario
        @param request
        @author Lorena Salamanca
    """        
    constructora = ConstructorCompany.objects.get(user_id=request.user.userprofile.id)
    properties = Property.objects.filter(constructor_company_id=constructora.id)
    owners = []
    for p in properties:
        p1 = p.properties_as_owner.all()
        for pr in p1:
            dataE = pr.user.first_name + " " + pr.user.last_name
            owners.append(dataE)
    owners_set = list(set(owners))
    return render(request, 'watchapp/rpt_admin_all_property_by_owner.html', { "request": request, "owners": owners_set, })
	
@login_required()
@user_passes_test(lambda u: u.groups.filter(name='constructoras').exists(), login_url='/watchapp/login/')
@csrf_exempt
def get_event_admin_all_property_by_owner(request):
    """
    Funcion que consulta los eventos de la constructora por propietario y mostrarlos en pantalla
    	@param request
    	@author Ricardo Restrepo
    """   
    # Array de eventos
    events = []
    #Parametros json enviados por ajax
    data = json.loads(request.body) 
    constructora = ConstructorCompany.objects.get(user_id=request.user.userprofile.id)
    print data['owners_select']
    if data['owners_select']=='0':
        properties = Property.objects.filter(constructor_company_id=constructora.id)
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']])
    else:
        owner_name= data['owners_select'].split( );
        owner_id = User.objects.get(first_name=owner_name[0])
        properties = Property.objects.filter(constructor_company_id=constructora.id, properties_as_owner=owner_id)
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']])

    if(len(events)==0): 
        return HttpResponse("0")
    else:
	# Collecion de eventos
	dataEvents=[]
	# Recorremos todos los eventos
	for e in events:
		dataE = {}	
		dataE["date"] = str(e.date.date())
		dataE["type"] = str(e.get_type_display())
		dataE["description"] = str(e.description.encode('utf8'))
		if (e.is_critical): 
		     dataE["is_critical"] = "Si" 
		else: 
		     dataE["is_critical"] ="No"
		if (e.is_fatal): 
		     dataE["is_fatal"] = "Si" 
		else: 
		     dataE["is_fatal"] = "No"
		dataE["property"] = e.property.name.encode('utf8')
		dataE["sensor"] = str(e.sensor.description.encode('utf8'))
		if data['owners_select']=='0' : dataE["propietario"] = str(e.property.properties_as_owner.all()[0].user.first_name.encode('utf8')) + ' ' + str(e.property.properties_as_owner.all()[0].user.last_name.encode('utf8'))
		else : dataE["propietario"] = data['owners_select']
		# Agregamos el evento a la coleccion
		dataEvents.append(dataE)
	    # Retornamos los eventos en formato JSON
        return HttpResponse(
                json.dumps(dataEvents),
                content_type="application/json"
            )

@login_required()
@user_passes_test(lambda u: u.groups.filter(name='constructoras').exists(), login_url='/watchapp/login/')
@csrf_exempt
def get_report_admin_all_property_by_owner(request):
    """
    Funcion que consulta los eventos de la constructora y genera el pdf 
    	@param request
    	@author Lorena Salamanca
    """   
    # Array de eventos
    events = []
    #Parametros json enviados por ajax
    data = json.loads(request.body) 
    pData=""

    # Consultamos todos los inmuebles de un propietario
    constructora = ConstructorCompany.objects.get(user_id=request.user.userprofile.id)
    properties = Property.objects.filter(constructor_company_id=constructora.id)
    if data['owners_select']=='0':
        properties = Property.objects.filter(constructor_company_id=constructora.id)
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']])
        pData = "Todos"
    else:
        owner_name= data['owners_select'].split( );
        owner_id = User.objects.get(first_name=owner_name[0])
        properties = Property.objects.filter(constructor_company_id=constructora.id, properties_as_owner=owner_id)
        events = Event.objects.filter(property__in=properties, date__range=[data['dateInit'], data['dateFinal']])
        pData=data['owners_select']
	
    if(len(events)==0): return HttpResponse("0")
    # Collecion de eventos
    dataEvents=[]
    # Recorremos todos los eventos
    for e in events:
        dataE = {}	
        dataE["date"] = str(e.date.date())
        dataE["type"] = str(e.get_type_display())
        dataE["description"] = str(e.description.encode('utf8'))
        if (e.is_critical): 
        	dataE["is_critical"] = "Si" 
        else: 
        	dataE["is_critical"] ="No"
        if (e.is_fatal): 
        	dataE["is_fatal"] = "Si" 
        else: 
        	dataE["is_fatal"] = "No"
        dataE["property"] = e.property.name.encode('utf8')
        dataE["sensor"] = str(e.sensor.description.encode('utf8'))
        if data['owners_select']=='0' : dataE["propietario"] = str(e.property.properties_as_owner.all()[0].user.first_name.encode('utf8')) + ' ' + str(e.property.properties_as_owner.all()[0].user.last_name.encode('utf8'))
        else : dataE["propietario"] = data['owners_select']
        # Agregamos el evento a la coleccion
        dataEvents.append(dataE)
    # Recuperamos el html del template del reporte
    print "va a invocar el pdf"
    html = render_to_string('watchapp/template_rpt_admin_all_property_by_owner.html', {'pagesize':'A4', 'events':dataEvents, 'event_type':str(pData), 'dateInit':str(data['dateInit']).split(' ')[0],'dateFinal':str(data['dateFinal']).split(' ')[0] }, context_instance=RequestContext(request))
    # Convertimos el html  a pdf    
    return generate_pdf(html)

def handle_uploaded_file(f, id):
	print(f.name)
	with open('smarthome/static/images/fredy.jpg', 'wb+') as destination:
		for chunk in f.chunks():
			destination.write(chunk)
