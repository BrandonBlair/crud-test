
const serverUrl='http://127.0.0.1:5000';


function postJoin(email, pw, cpw) {
  var path = "/v1/join";
  var url = serverUrl + path;
  var Http = new XMLHttpRequest();
  Http.open("POST", url, false);  // Boy, forgetting to set this to false wastes a lot of dev hours
  Http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
  Http.send("email=" + email + "&password=" + pw + "&confirm_password=" + cpw);

  var resp = Http.response;
  var status = Http.status;
  var body = resp.details;
  var error = resp.error;
  var view = {status: status, body: body, error: error};
  return view
}

function postLogin(email, password) {
  console.log(email + " " + password);
  var path = "/v1/login";
  var url = serverUrl + path;
  var xhr = new XMLHttpRequest();
  xhr.open("POST", url, false);
  xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
  xhr.send("email=" + email + "&password=" + password);

  console.log(xhr.getAllResponseHeaders());
  return {status: xhr.status, body: xhr.responseText};
}

function getSearch(author, title, isbn) {
  var path = "/v1/search";
  var url = serverUrl + path;
  var qs = "?";
  var prefix = "";

  if (author.length > 1) {
    qs = qs.concat(prefix + "author=" + author);
    prefix = "&";
  }

  if (title.length > 1) {
    qs = qs.concat(prefix + "title=" + title);
    prefix = "&";
  }

  if (isbn.length > 1) {
    qs = qs.concat(prefix + "isbn=" + isbn);
    prefix = "&";
  }

  url = url.concat(qs);
  var xhr = new XMLHttpRequest();
  xhr.open("GET", url, false);
  xhr.send(null);
  return {status: xhr.status, body: xhr.responseText};

}

function postResource(title, authorFirst, authorMiddle, authorLast, edition, isbn10, isbn13) {
  var path = "/v1/resource";
  var url = serverUrl + path;
  var Http = new XMLHttpRequest();
  Http.open("POST", url, false);
  Http.setRequestHeader("Content-type", "application/json");

  var body = JSON.stringify(
    {
      "title": title,
      "authorFirst": authorFirst,
      "authorMiddle": authorMiddle,
      "authorLast": authorLast,
      "edition": edition,
      "isbn10": isbn10,
      "isbn13": isbn13,
    }
  );
  Http.send(body);

  var resp = Http.response;
  var status = Http.status;
  var body = resp.details;
  var error = resp.error;
  var view = {status: status, body: body, error: error};
  return view
}
