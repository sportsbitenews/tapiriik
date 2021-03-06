from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from tapiriik.services import Service
from tapiriik.auth import User
import json
from tapiriik.services.RunnersConnect import RunnersConnectService


def authredirect(req, service, level=None):
    svc = Service.FromID(service)
    return redirect(svc.GenerateUserAuthorizationURL(req.session, level))

def authreturn(req, service, level=None):
    if ("error" in req.GET or "not_approved" in req.GET):
        success = False
    else:
        svc = Service.FromID(service)
        try:
            uid, authData = svc.RetrieveAuthorizationToken(req, level)
        except Exception as e:
            return render(req, "oauth-failure.html", {
                "service": svc,
                "error": str(e)
            })
        serviceRecord = Service.EnsureServiceRecordWithAuth(svc, uid, authData)

        # auth by this service connection
        existingUser = User.AuthByService(serviceRecord)
        # only log us in as this different user in the case that we don't already have an account
        if req.user is None and existingUser is not None:
            User.Login(existingUser, req)
        else:
            User.Ensure(req)
        # link service to user account, possible merge happens behind the scenes (but doesn't effect active user)
        User.ConnectService(req.user, serviceRecord)
        success = True

    return render(req, "oauth-return.html", {"success": 1 if success else 0})

def authrc(req):
    token = req.GET.get('token')

    if token is None:
        return redirect("https://app.runnersconnect.net")

    user = User.EnsureWithRcToken(req, token)
    uid, authData, extendedAuthData = (token, {}, {"token": token})
    serviceRecord = Service.EnsureServiceRecordWithAuth(RunnersConnectService, uid, authData, extendedAuthData, True)
    User.ConnectService(user, serviceRecord)

    return redirect("http://sync.runnersconnect.net/")
