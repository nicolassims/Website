<?php

if (isset($_POST['submit'])) {
	$name = $_POST['name'];
	$subject = $_POST['subject'];
	$mailFrom = $_POST['email'];
	$message = $_POST['message'];

	$mailTo = "neskarayakaylar@freudiancreations.website"//get around emails being blocked by google
	$headers = "From: ".$mailFrom;
	$txt = "You have received an email from ".$name.".\n\n".$message;

	mail($mailTo, $subject, $txt, $headers);
}

/*
$errors = "";
$myemail = 'neskarayakaylar@gmail.com';

if (empty($_POST['name']) || empty($_POST['email']) || empty($_POST['message'])) {
	$errors .= "\n Error: all fields are required";
}

$name = $_POST['name'];
$email_address = $_POST['email'];
$message = $_POST['message'];

if (!preg_match("/^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,3})$/i", $email_address)) {
	$errors .= "\n Error: Invalid email address";
}

if (empty($errors)) {

$to = $myemail;
$email_subject = "Contact form submission: $name";
$email_body = 

"You have received a new message. ".
" Here are the details:\n Name: $name \n ".
"Email: $email_address\n Message \n $message";

$headers = "From: $myemail\n";
$headers .= "Reply-To: $email_address";

mail($to,$email_subject,$email_body,$headers);

//redirect to the 'thank you' page

//header('Location: contact-form-thank-you.html');

}*/

?>