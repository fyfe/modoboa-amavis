(function(app) {
    "use strict";

    var module = {};

    module.init_view = function() {
        self._list_table = document.getElementById("wblist")
        self.hard_bw_mode = self._list_table.dataset.bwlHardBwMode

        var rows = self._list_table.querySelectorAll("tbody > tr");
        for (var i = 0, row; row = rows[i++]; ) {
            var cmd_cell = row.querySelector(".td-commands");
            if (!cmd_cell) {
                continue;
            }
            var button = _create_button(
                "glyphicon-trash", _delete_button_action
            );
            cmd_cell.appendChild(button)
        }
    };

    module.set_page_urls = function(action_urls) {
        this.action_urls = action_urls
        return this;
    };

    module.create = function() {
        var url = this.action_urls["create"];
        return this;
    }

    module.delete = function(id) {
        var url = this.action_urls["delete"].replace("_ID_", id);
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function() {
            if(xhr.readyState == XMLHttpRequest.DONE && xhr.status == 204) {
                row = document.getElementById(id);
                if (row) {
                    row.class += " danger";
                    setTimeout(function() {
                        row.remove();
                    }, 10000);
                }
            }
        };
        xhr.onerror = function(event) {
            console.error(event);
        };
        xhr.open("DELETE", url)
        xhr.setRequestHeader("Accept", "text/javascript");
        xhr.send();
        return this;
    }

    module.edit = function(id) {
        var url = this.action_urls["edit"];
        return this;
    }

    _create_button = function(icon, onclick) {
        var icon_span = document.createElement("span");
        icon_span.class = "glyphicon " + icon;
        var button = document.createElement("button");
        button.onclick = onclick;
        button.appendChild(icon_span);
        return button;
    };

    _delete_button_action = function(event) {
        var row = self.closest("tr");
        if (row.id) {
            var cancel = confirm(gettext("Are you sure you want to delete " +
                                         "this entry?"));
            if (!cancel) {
                module.delete(row.id);
            }
        }
        return True;
    };

    app.bwlist = module;

}(ModoboaAmavis));
