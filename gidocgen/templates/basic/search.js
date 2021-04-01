// SPDX-FileCopyrightText: 2021 GNOME Foundation
//
// SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

(function() {

const QUERY_TYPES = [
    "alias",
    "bitfield",
    "callback",
    "class",
    "constant",
    "ctor",
    "domain",
    "enum",
    "function_macro",
    "function",
    "interface",
    "method",
    "property",
    "record",
    "signal",
    "type_func",
    "union",
    "vfunc",
];
const QUERY_PATTERN = new RegExp("^(" + QUERY_TYPES.join('|') + ")\\s*:\\s*", 'i');


const fzy = window.fzy;
const searchParams = getSearchParams();

let searchIndex = undefined;

// Exports
window.onInitSearch = onInitSearch;

/* Event handlers */

function onInitSearch() {
    fetchJSON('index.json', onDidLoadSearchIndex);
}

function onDidLoadSearchIndex(data) {
    const searchInput = getSearchInput();
    const searchIndex = new SearchIndex(data)

    if (searchInput.value === "") {
        searchInput.value === searchParams.q || "";
    }

    function runQuery(query) {
        const q = matchQuery(query);
        const docs = searchIndex.searchDocs(q.term, q.type);

        const results = docs.map(function(doc) {
            return {
                name: doc.name,
                type: doc.type,
                text: getTextForDocument(doc, searchIndex.meta),
                href: getLinkForDocument(doc),
                summary: doc.summary,
            };
        });

        return results;
    }

    function search() {
        const query = searchParams.q;
        if (searchInput.value === "" && query) {
            searchInput.value = query;
        }
        window.title = "Results for: " + query.user;
        showResults(query, runQuery(query));
    }

    window.onpageshow = function() {
        var query = getQuery(searchParams.q);
        if (searchInput.value === "" && query) {
            searchInput.value = query.user;
        }
        search();
    };

    if (searchParams.q) {
        search();
    }
};


/* Rendering */

function showSearchResults(search) {
    if (search === null || typeof search === 'undefined') {
        search = getSearchElement();
    }

    addClass(main, "hidden");
    removeClass(search, "hidden");

}

function hideSearchResults(search) {
    if (search === null || typeof search === 'undefined') {
        search = getSearchElement();
    }

    addClass(search, "hidden");
    removeClass(search, "hidden");
}

function addResults(results) {
    var output = "";

    if (results.length > 0) {
        output += "<table class=\"results\">" +
                    "<tr><th>Name</th><th>Description</th></tr>";

        results.forEach(function(item) {
            output += "<tr>" +
                        "<td class=\"result " + item.type + "\">" +
                        "<a href=\"" + item.href + "\"><code>" + item.text + "</code></a>" +
                        "</td>" +
                        "<td>" + item.summary + "</td>" +
                        "</tr>";
        });

        output += "</table>";
    } else {
        output = "No results found.";
    }

    return output;
}

function showResults(query, results) {
    const search = getSearchElement();
    const output =
        "<h1>Results for &quot;" + query + "&quot; (" + results.length + ")</h1>" +
        "<div id=\"search-results\">" +
            addResults(results) +
        "</div>";

    search.innerHTML = output;
    showSearchResults(search);
}


/* Search data instance */

function SearchIndex(searchIndex) {
    this.symbols = searchIndex.symbols;
    this.meta = searchIndex.meta;
}
SearchIndex.prototype.searchDocs = function searchDocs(term, type) {
    const filteredSymbols = type ? this.symbols.filter(s => s.type === type) : this.symbols;
    const results = fzy.filter(term, filteredSymbols, doc => getTextForDocument(doc, this.meta))
    return results.map(i => i.item)
}
SearchIndex.prototype.getDocumentFromId = function getDocumentFromId(id) {
    if (typeof id === "number") {
        return this.searchIndex.symbols[id];
    }
    return null;
}


/* Search metadata selectors */

function getLinkForDocument(doc) {
    switch (doc.type) {
        case "alias": return "alias." + doc.name + ".html";
        case "bitfield": return "flags." + doc.name + ".html";
        case "callback": return "callback." + doc.name + ".html";
        case "class": return "class." + doc.name + ".html";
        case "class_method": return "class_method." + doc.type_name + "." + doc.name + ".html";
        case "constant": return "const." + doc.name + ".html";
        case "ctor": return "ctor." + doc.type_name + "." + doc.name + ".html";
        case "domain": return "error." + doc.name + ".html";
        case "enum": return "enum." + doc.name + ".html";
        case "function": return "func." + doc.name + ".html";
        case "function_macro": return "func." + doc.name + ".html";
        case "interface": return "iface." + doc.name + ".html";
        case "method": return "method." + doc.type_name + "." + doc.name + ".html";
        case "property": return "property." + doc.type_name + "." + doc.name + ".html";
        case "record": return "struct." + doc.name + ".html";
        case "signal": return "signal." + doc.type_name + "." + doc.name + ".html";
        case "type_func": return "type_func." + doc.type_name + "." + doc.name + ".html";
        case "union": return "union." + doc.name + ".html";
        case "vfunc": return "vfunc." + doc.type_name + "." + doc.name + ".html";
    }
    return null;
}

function getTextForDocument(doc, meta) {
    switch (doc.type) {
        case "alias":
        case "bitfield":
        case "class":
        case "domain":
        case "enum":
        case "interface":
        case "record":
        case "union":
            return doc.ctype;
        case "class_method":
        case "constant":
        case "ctor":
        case "function":
        case "function_macro":
        case "method":
        case "type_func":
            return doc.ident;

        // NOTE: meta.ns added for more consistent results, otherwise
        // searching for "Button" would return all signals, properties
        // and vfuncs (eg "Button.clicked") before the actual object 
        // (eg "GtkButton") because "Button" matches higher with starting
        // sequences.
        case "property":
            return meta.ns + doc.type_name + ":" + doc.name;
        case "signal":
            return meta.ns + doc.type_name + "::" + doc.name;
        case "vfunc":
            return meta.ns + doc.type_name + "." + doc.name;

        case "callback":
            return doc.name;
    }

    return null;
}


// Helpers

function fetchJSON(url, callback) {
    const request = new XMLHttpRequest();
    request.open('GET', url, true);
    request.onreadystatechange = function() {
        if (request.readyState === XMLHttpRequest.DONE) {
            const status = request.status;

            if (status === 0 || (status >= 200 && status < 400)) {
                callback(JSON.parse(request.responseText));
            }
        }
    }
    request.send(null);
}

function getSearchElement() {
    return document.getElementById("search");
}

function getSearchInput() {
    return document.getElementsByClassName("search-input")[0];
}

function getSearchParams() {
    const params = {};
    window.location.search.substring(1).split('&')
        .map(function(s) {
            const pair = s.split('=');
            params[decodeURIComponent(pair[0])] =
                typeof pair[1] === 'undefined' ? null : decodeURIComponent(pair[1].replace(/\+/g, '%20'));
        });
    return params;
}

function matchQuery(input) {
    let type = null
    let term = input

    const matches = term.match(QUERY_PATTERN);
    if (matches) {
        type = matches[1];
        term = term.substring(matches[0].length);
    }

    // Remove all spaces, fzy will handle things gracefully.
    term = term.replace(/\s+/g, '')

    return { type: type, term: term }
}

})()
