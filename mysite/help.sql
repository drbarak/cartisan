# source mysite/help.sql;
# system <command>, such as 'system ls' to see the folder listing

USE drbarak$hashi;
SHOW TABLES;
DROP TABLE IF EXISTS seat;
DROP TABLE IF EXISTS zone;
DROP TABLE IF EXISTS hall;
SHOW TABLES;

CREATE TABLE hall(
    id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,             /* קוד אולם (ללקוח יכולים להיות מספר אולמות, כגון מספר אולמות במיתח */
    client_id INT,                           /*  קוד לקוח (הלקוחות מנוהלים במערכת המרכזית) */
    name VARCHAR(255) NOT NULL DEFAULT '',  /*  שם אולם */
    picture VARCHAR(255),                           /* תמונת המקום  */
    directions VARCHAR(255),                 /*  דרכי הגעה */
    INDEX idx_client (client_id, id)
    );

INSERT INTO hall(client_id, picture, name) VALUES
(1, 'hall1.png', 'הבימה')
, (1, 'hall2.jpg', 'צוותא');


CREATE TABLE zone(
    id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,             /* קוד איזור */
    name VARCHAR(255) NOT NULL DEFAULT '',                  /* שם איזור (יציע, אולם, VIP וכד') */
    hall_id INT,
    client_id INT,
    marked_seats TINYINT NOT NULL DEFAULT False,                            /* מקומות משוריינים/חופשיים */
    max_seats INT NOT NULL,                                           /* מיכסה מירבית */
    FOREIGN KEY(hall_id) REFERENCES hall(id) ON DELETE CASCADE
    );

INSERT INTO zone(client_id, hall_id) VALUES
(1, 1), (1, 1);

CREATE TABLE seat(
    zone_id INT NOT NULL,
    hall_id INT NOT NULL,
    client_id INT NOT NULL,
    row INT NOT NULL,
    seat INT NOT NULL,
    status TINYINT NOT NULL DEFAULT False,
    FOREIGN KEY(zone_id) REFERENCES zone(id) ON DELETE CASCADE,
    FOREIGN KEY(hall_id) REFERENCES hall(id) ON DELETE CASCADE,
    PRIMARY KEY (client_id, hall_id, zone_id, row, seat)
    );

INSERT INTO seat(client_id, hall_id, zone_id, row, seat) VALUES
(1, 1, 1, 10, 3), (1, 1, 1, 10, 4);

DROP TABLE IF EXISTS user_login;
CREATE TABLE `user_login` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `login_dt` datetime NOT NULL DEFAULT NOW(),
  `ip_address` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ip` (`ip_address`)
);

DROP TABLE IF EXISTS log;
CREATE TABLE `log` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `login_dt` datetime NOT NULL DEFAULT NOW(),
  `line` text DEFAULT NULL,
  PRIMARY KEY (`id`)
);

