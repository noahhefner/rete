# Notes

**Alpha** nodes evaluate conditions involving a **single** fact.
**Beta** nodes evaluate conditions involving **multiple** facts.

For example:

```
person.age >= 18 &&
person.country == "US" &&
person.id == work.person_id &&
work.salary > 100000
```

can be split into:

```
Person Alpha:
    age >= 18
    country == "US"

WorksAt Alpha:
    salary > 100000

Beta:
    person.id == work.person_id
```