
const serverUrl='http://127.0.0.1:5000';


function postJoin(email, pw, cpw) {
  var path = "/v1/join";
  var url = serverUrl + path;
  var Http = new XMLHttpRequest();
  Http.open("POST", url);
  Http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
  Http.send("email=" + email + "&password=" + pw + "&confirm_password=" + cpw);

  Http.onreadystatechange = (e) => {
    console.log(Http.responseText);
  }
}

function postLogin(email, password) {
  var path = "/v1/login";
  var url = serverUrl + path;

  xhr.open("POST", url, false);
  Http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
  Http.send("email=" + email + "&password=" + pw);
  return xhr.responseText;
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
  return xhr.responseText;

}

function postResource(title, author_first, author_middle, author_last, edition, isbn10, isbn13) {
  var path = "/v1/resource";
  var url = serverUrl + path;
  var Http = new XMLHttpRequest();
  Http.open("POST", url);
  Http.setRequestHeader("Content-type", "application/json");

  var body = JSON.stringify(
    {
      "title": title,
      "author_first": author_first,
      "author_middle": author_middle,
      "author_last": author_last,
      "edition": edition,
      "isbn10": isbn10,
      "isbn13": isbn13,
    }
  );
  Http.send(body);

  Http.onreadystatechange = (e) => {
    console.log(Http.responseText);
  }
}
