(function(app) {
    "use strict";

    var module = {};

    var _create_button = function(icon, type, onclick) {
        var icon_span = document.createElement("span");
        icon_span.className = "glyphicon " + icon;
        var button = document.createElement("button");
        button.className = "btn " + type;
        button.onclick = onclick;
        button.appendChild(icon_span);
        return button;
    };

    var _delete_button_action = function(event) {
        event.stopPropagation();
        var row = event.target.closest("tr");
        if (row.id) {
            var cb = function(mail_id) {
                console.log("Message deleted " + mail_id);
            };
            var do_action = confirm(gettext("Are you sure you want to delete " +
                                            "this entry?"));
            if (do_action) {
                module.delete(row.id, cb);
            }
        }
        return true;
    };

    var _row_click_action = function(event) {
        event.stopPropagation();
        var row = event.target.closest("tr");
        if (row.id) {
            var url = app.quarantine.action_urls["view"]
                .replace("_MAIL_ID_", row.id);
            if (event.ctrlKey || event.metaKey) {
                window.open(url, "_blank");
            }
            else {
                document.location = url;
            }
        }
        return true;
    };

    module.init_list_view = function() {
        this._list_table = document.getElementById("quarantine_list");
        var rows = this._list_table.querySelectorAll("tbody > tr");
        for (var i = 0, row; row = rows[i++]; ) {
            var cmd_cell = row.querySelector(".td-commands");
            if (!cmd_cell) {
                continue;
            }
            var button = _create_button(
                "glyphicon-trash", "btn-danger", _delete_button_action
            );
            cmd_cell.appendChild(button);
            row.onclick = _row_click_action;
        }
        return this;
    };

    module.init_detail_view = function() {
        var quarantined_message = document.getElementById("quarantined_message");
        var btn_return_to_list = document.getElementById("btn_return_to_list");
        if (btn_return_to_list) {
            btn_return_to_list.onclick = function(event) {
                history.go(-1);
                return true;
            };
        }

        var btn_release = document.getElementById("btn_release");
        if (btn_release) {
            btn_release.onclick = function(event) {
                event.stopPropagation();
                var mail_id = quarantined_message.dataset.mailId;
                var cb = function(mail_id) {
                    console.log("Message released " + mail_id);
                };
                module.release(mail_id, cb);
            };
        }

        var btn_delete = document.getElementById("btn_delete");
        if (btn_delete) {
            btn_delete.onclick = function(event) {
                event.stopPropagation();
                var mail_id = quarantined_message.dataset.mailId;
                var cb = function(mail_id) {
                    console.log("Message deleted " + mail_id);
                };
                var do_action = confirm(
                    gettext("Are you sure you want to delete this message?")
                );
                if (do_action) {
                    module.delete(mail_id, cb);
                }
            };
        }

        var btn_mark_as_spam = document.getElementById("btn_mark_as_spam");
        if (btn_mark_as_spam) {
            btn_mark_as_spam.onclick = function(event) {
                event.stopPropagation();
                var mail_id = quarantined_message.dataset.mailId;
                var cb = function(mail_id) {
                    console.log("Message marked as spam " + mail_id);
                };
                module.mark_as("spam", mail_id, cb);
            };
        }

        var btn_mark_as_ham = document.getElementById("btn_mark_as_ham");
        if (btn_mark_as_ham) {
            btn_mark_as_ham.onclick = function(event) {
                event.stopPropagation();
                var mail_id = quarantined_message.dataset.mailId;
                var cb = function(mail_id) {
                    console.log("Message marked as ham " + mail_id);
                };
                module.mark_as("ham", mail_id, cb);
            };
        }

        var btn_view_full_headers = document.getElementById("btn_view_full_headers");
        if (btn_view_full_headers) {
            var headers = document.getElementById("headers");
            var full_headers = document.getElementById("full_headers");
            var btn_label = document.getElementById("view_full_headers_label");
            btn_view_full_headers.onclick = function(event) {
                event.stopPropagation();
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
                return true;
            };
        }

        return module;
    };

    module.set_page_urls = function(action_urls) {
        this.action_urls = action_urls;
        return this;
    };

    var _rest_action = function(method, action, id, cb) {
        var url = module.action_urls[action].replace("_MAIL_ID_", id);
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if(xhr.readyState == XMLHttpRequest.DONE && xhr.status == 204) {
                cb(id);
            }
        };
        xhr.onerror = function(event) {
            console.error(event);
        };
        xhr.open(method, url);
        xhr.setRequestHeader("Accept", "application/json; indent=4");
        xhr.setRequestHeader("X-CSRFToken", Cookies.get("csrftoken"));
        xhr.send();
    };

    module.delete = function(id, cb) {
        _rest_action("DELETE", "delete", id, cb);
    };

    module.release = function(id, cb) {
        _rest_action("POST", "release", id, cb);
    };

    module.mark_as = function(action, id, cb) {
        _rest_action("POST", "mark_as_" + action, id, cb);
    };

    app.quarantine = module;

}(ModoboaAmavis));
