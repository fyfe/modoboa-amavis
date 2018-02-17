(function(app) {
    "use strict";

    app.quarantine
        .init({
            "index": "{% url 'modoboa_amavis:index' %}",
            "view": "{% url 'modoboa_amavis:quarantine_message' mail_id='_MAIL_ID_' %}",

            "api:list": "{% url 'api:quarantine-list' %}",
            "api:requests": "{% url 'api:quarantine-requests' %}",
            "api:detail": "{% url 'api:quarantine-detail' mail_id='_MAIL_ID_' %}",
            "api:delete": "{% url 'api:quarantine-delete' mail_id='_MAIL_ID_' %}",
            "api:bulk-delete": "{% url 'api:quarantine-bulk-delete' %}",
            "api:release": "{% url 'api:quarantine-release' mail_id='_MAIL_ID_' %}",
            "api:bulk-release": "{% url 'api:quarantine-bulk-release' %}",
            "api:mark-as-ham": "{% url 'api:quarantine-mark-as-ham' mail_id='_MAIL_ID_' %}",
            "api:mark-as-spam": "{% url 'api:quarantine-mark-as-spam' mail_id='_MAIL_ID_' %}",
        });

}(ModoboaAmavis));
