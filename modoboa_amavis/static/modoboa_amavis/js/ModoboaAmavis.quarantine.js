(function(app) {
    "use strict";

    var module = {};

    var action_cb = function(response, alert_class) {
        var alert_box = document.getElementById("alert_box");
        var message = alert_box.getElementsByClassName("message")[0];
        message.innerHTML = response["detail"];
        alert_box.classList.remove("alert-success");
        alert_box.classList.remove("alert-danger");
        alert_box.classList.add(alert_class);
        alert_box.classList.remove("hidden");
        if (alert_class == "alert-success") {
            setTimeout(function() {
                document.getElementById("alert_box").classList.add("hidden");
                history.back();
            }, 5000);
        }
        else {
            console.error(response);
        }
    };

    var action_return_to_list = function(event) {
        event.stopPropagation();
        history.back();
        return false;
    };

    var action_delete = function(event) {
        event.stopPropagation();
        var mail_id = (
            document.getElementById("quarantined_message").dataset.mailId
        );
        var message = gettext("Are you sure you want to delete this message?");
        if (confirm(message)) {
            module.delete(mail_id, action_cb);
        }
        return false;
    };

    var action_release = function(event) {
        event.stopPropagation();
        var mail_id = (
            document.getElementById("quarantined_message").dataset.mailId
        );
        var message = gettext("Are you sure you want to release this message?");
        if (confirm(message)) {
            module.release(mail_id, action_cb);
        }
        return false;
    };

    var action_mark_as_ham = function(event) {
        event.stopPropagation();
        var mail_id = (
            document.getElementById("quarantined_message").dataset.mailId
        );
        var message = gettext("Are you sure you want to mark this message as not spam?");
        if (confirm(message)) {
            module.mark_as_ham(mail_id, action_cb);
        }
        return false;
    };

    var action_mark_as_spam = function(event) {
        event.stopPropagation();
        var mail_id = (
            document.getElementById("quarantined_message").dataset.mailId
        );
        var message = gettext("Are you sure you want to mark this message as spam?");
        if (confirm(message)) {
            module.mark_as_spam(mail_id, action_cb);
        }
        return false;
    };

    var action_view_headers = function(event) {
        event.stopPropagation();
        var headers = document.getElementById("headers");
        var full_headers = document.getElementById("full_headers");
        var btn_label = document.getElementById("view_full_headers_label");
        var view_full_headers =  !(
            btn_view_full_headers.dataset.viewFullHeaders === "true"
        );
        btn_view_full_headers.dataset.viewFullHeaders =
            view_full_headers;
        if (view_full_headers) {
            full_headers.classList.remove("hidden");
            headers.classList.add("hidden");
            btn_label.textContent =
                btn_view_full_headers.dataset.labelHide;
        }
        else {
            full_headers.classList.add("hidden");
            headers.classList.remove("hidden");
            btn_label.textContent =
                btn_view_full_headers.dataset.labelShow;
        }
        return false;
    };

    var rest_action = function(method, action, id, cb, data) {
        var url = module.action_urls[action].replace("_MAIL_ID_", id);
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if(xhr.readyState == XMLHttpRequest.DONE) {
                var response = JSON.parse(xhr.response);
                if (xhr.status == 200) {
                    cb(response, "alert-success");
                }
                else {
                    cb(response, "alert-danger");
                }
            }
        };
        xhr.onerror = function(event) {
            console.error(event);
        };
        xhr.open(method, url);
        xhr.setRequestHeader("Accept", "application/json");
        xhr.setRequestHeader("X-CSRFToken", Cookies.get("csrftoken"));
        if (data) {
            xhr.setRequestHeader("Content-Type", "application/json");
            xhr.send(JSON.stringify(data));
        }
        else {
            xhr.send();
        }
    };

    module.delete = function(id, cb) {
        rest_action("DELETE", "api:delete", id, cb);
    };

    module.release = function(id, cb) {
        rest_action("POST", "api:release", id, cb);
    };

    module.mark_as_ham = function(id, cb) {
        // TODO: use bootstrap modal dialog to get recipient_db
        rest_action("POST", "api:mark-as-ham", id, cb, {"recipient_db": "user"});
    };

    module.mark_as_spam = function(id, cb) {
        // TODO: use bootstrap modal dialog to get recipient_db
        rest_action("POST", "api:mark-as-spam", id, cb, {"recipient_db": "user"});
    };

    var init_detail_view = function() {
        document.getElementById("btn_return_to_list").onclick = action_return_to_list;
        document.getElementById("btn_release").onclick = action_release;
        document.getElementById("btn_delete").onclick = action_delete;
        document.getElementById("btn_mark_as_spam").onclick = action_mark_as_spam;
        document.getElementById("btn_mark_as_ham").onclick = action_mark_as_ham;
        document.getElementById("btn_view_full_headers").onclick = action_view_headers;
    };

    module.init = function(action_urls) {
        module.action_urls = action_urls;
        if (document.getElementById("quarantined_message"))
            init_detail_view();
        return module;
    };

    app.quarantine = module;

}(ModoboaAmavis));
