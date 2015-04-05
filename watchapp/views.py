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
        asresident = False;
        if request.POST.get('select_as_owner', '') == "0":
            selected_property = Property.objects.get(name=request.POST.get('select_as_resident', ''))
            sensors = property_sensors(request,selected_property.id)
            asresident = True;
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
def change_secure_mode(request, property_id):
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

        return render(request, 'watchapp/users_home.html', {
        "selected_property": selected_property,
        "request": request,
        "Sensors":sensors,
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
    #sensors = Sensor.objects.filter(property_id=request.POST["select_Property"])
    sensors = Sensor.objects.filter(property_id=property_id)
    #log.debug("property_sensors " + str(sensors[0].description))
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
    #return render(request,"watchapp/sensorstatus.html",{ 
    #        "propertyList": propertyList, 
    #    })
    #log.debug("propertys_by_User " + propertyList[0].name)
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
    #log.debug("update_value: GET val: " + str(request))
    if request.method == 'GET':
        selected_property = Property.objects.get(pk=property_id)
        sensors = property_sensors(request,selected_property.id)
        return render(request, 'watchapp/users_home.html', {
        "selected_property": selected_property,
        "asresident":asresident,
        "request": request,
        "Sensors":sensors,
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
    return HttpResponse("Usuario constructora autenticado")

####################### Vista para rest_framework #######################

class EventViewSet(viewsets.ModelViewSet):
   """
   Esta funcion es el API endpoint que permite hacer peticiones GET / POST a eventos.
	     @param viewsets
		 @author Lorena Salamanca
   """
   queryset = Event.objects.all()
   serializer_class = EventSerializer
