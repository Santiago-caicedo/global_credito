from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

def login_view(request):
    """
    Maneja el inicio de sesión de los usuarios y los redirige
    según su rol.
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil'):
            if request.user.perfil.rol == 'ASPIRANTE':
                return redirect('aspirante_escritorio')
            elif request.user.perfil.rol == 'ANALISTA':
                return redirect('analista_escritorio')
            elif request.user.perfil.rol == 'DIRECTOR':
                return redirect('director_escritorio')
        return redirect('/')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
            # Ahora pasamos el objeto 'request' a la función authenticate.
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                # Redirección según el rol
                if hasattr(user, 'perfil'):
                    if user.perfil.rol == 'ASPIRANTE':
                        return redirect('aspirante_escritorio')
                    elif user.perfil.rol == 'ANALISTA':
                        return redirect('analista_escritorio')
                    elif user.perfil.rol == 'DIRECTOR':
                        return redirect('director_escritorio')
                return redirect('/')
            else:
                messages.error(request, "Nombre de usuario o contraseña incorrectos.")
        else:
            messages.error(request, "Nombre de usuario o contraseña incorrectos.")
    
    form = AuthenticationForm()
    return render(request, "usuarios/login.html", {"form": form})


