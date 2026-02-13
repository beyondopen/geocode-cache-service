ALTER TABLE location ADD COLUMN district text;
ALTER TABLE location ADD COLUMN street text;
ALTER TABLE location ADD COLUMN postal_code text;
ALTER TABLE location ADD COLUMN house_number text;

ALTER TABLE location DROP CONSTRAINT location_index;
ALTER TABLE location ADD CONSTRAINT location_index UNIQUE (city, county, state, country, district, street, postal_code, house_number);
