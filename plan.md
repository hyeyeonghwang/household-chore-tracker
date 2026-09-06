# Shared Household Chore Assignment Tool — MVP Scope

## Core Product Definition

A **shared household chore assignment tool** that:

- automatically rotates chores **weekly**
- uses **simple turn-taking**
- allows **any household member** to manually reassign a chore when needed
- focuses primarily on **assignment**, not productivity tracking or gamification

## Finalized Core Decisions

### 1. Primary Goal: Assignment

The most important goal of the tool is **assigning household chores**.

The product should make it clear who is responsible for each chore, rather than trying to solve every household-management problem at once.

### 2. Default Assignment Model: Automatic Rotation

Chores should be assigned automatically rather than requiring someone to manually distribute them every week.

**Why this option was chosen**

Automatic rotation removes recurring coordination work and avoids requiring one person to act as the household manager.

**Other options considered**

- Manual assignment
- Self-claiming chores
- Rule-based assignment using preferences or availability
- Hybrid automatic/manual assignment

These could be added later, but automatic rotation best matches the main goal of reducing assignment overhead.

### 3. Fairness Model: Simple Turn-Taking

The default rotation should use a simple sequence among household members.

Example:

```text
Trash: A -> B -> C -> A
```

**Why this option was chosen**

Simple turn-taking is:

- predictable
- easy to understand
- easy to implement
- easy to verify as fair

**Other options considered**

- Equal total number of chores
- Weighted workload based on difficulty or time
- Optimization based on historical workload

These approaches may be fairer in some households, but they introduce significantly more complexity and require additional data.

### 4. Rotation Frequency: Weekly

Assignments rotate once per week.

**Why this option was chosen**

Weekly rotation is frequent enough to distribute responsibility while avoiding constant assignment changes.

**Other options considered**

- Daily rotation
- Rotation after every completion
- Custom frequency for each chore

Per-chore schedules are useful, but they make the first version considerably more complicated.

### 5. Exception Handling: Manual Reassignment

If someone cannot do their assigned chore, the chore can be manually reassigned.

Any household member is allowed to perform the reassignment.

**Why this option was chosen**

Exceptions are inevitable. Manual reassignment provides flexibility without requiring the system to model availability, schedules, preferences, or complex swapping rules.

**Other options considered**

- Automatically skip unavailable members
- Allow formal swaps between members
- Restrict reassignment to an admin
- Prevent exceptions in the MVP

Allowing any member to reassign keeps the household collaborative and avoids creating an unnecessary administrator role.

---

# Additional MVP Decisions

## 6. One Shared Household Space

Each household has:

- one member list
- one chore list
- one shared weekly assignment view

**Why**

The rotation system needs a clearly defined set of people and chores.

**Other options considered**

- Multiple rooms or groups
- Separate chore pools
- Multiple households per user

These are useful extensions but are unnecessary for validating the core product.

---

## 7. One Assignee Per Chore Per Week

Each chore has exactly one responsible person during a weekly cycle.

Example:

| Chore | This Week |
|---|---|
| Trash | Alex |
| Bathroom | Mina |
| Vacuum | Chris |

**Why**

A single assignee creates clear ownership.

**Other options considered**

- Multiple assignees
- Primary and backup assignees
- Shared chores without an owner

These make accountability and rotation behavior less clear.

---

## 8. Independent Rotation Per Chore

Each chore maintains its own rotation position.

Example:

```text
Trash:     A -> B -> C
Bathroom:  B -> C -> A
Vacuum:    C -> A -> B
```

**Why**

This prevents every member from receiving the same bundle of chores each week and produces more varied assignments.

**Alternative considered**

Rotate the entire chore list as one bundle.

That would be simpler technically, but could repeatedly give people the same combinations of chores.

---

## 9. Manual Reassignment Only Affects the Current Week

A reassignment is treated as a temporary exception.

Example normal rotation:

```text
A -> B -> C -> A
```

If B is assigned this week but the chore is manually reassigned to C, the underlying rotation does not change.

The next scheduled person remains C.

**Why**

Temporary exceptions should not silently modify the long-term rotation sequence.

**Alternative considered**

Count the reassignment as part of the rotation history.

This could create confusing future assignments after a one-time exception.

---

## 10. One Household-Defined Rotation Day

Each household selects one weekly rotation day, such as Monday.

All chore assignments change on that day.

**Why**

A single rotation boundary makes the system easy to understand.

**Other options considered**

- Always rotate on Monday
- Rolling seven-day periods
- Different rotation days for each chore

A household-level setting provides useful flexibility without adding much complexity.

---

## 11. New Members Join on the Next Rotation

If a new household member is added during the week, current assignments remain unchanged.

The new member enters the rotation starting with the next weekly cycle.

**Why**

Adding someone should not unexpectedly reshuffle responsibilities that are already active.

**Alternative considered**

Immediately rebalance all assignments.

This could be fair mathematically but disruptive in practice.

---

## 12. Removing a Member

If someone leaves the household:

- their active chores become **unassigned**
- any member can manually reassign those chores
- future rotations exclude the removed member

**Why**

Automatically transferring all of that person's chores could unexpectedly overload another member.

**Alternative considered**

Automatically assign each chore to the next person in the sequence.

This could be added later if users prefer more automation.

---

## 13. Minimal Completion Tracking

Each weekly chore assignment has only two states:

- **Pending**
- **Done**

**Why**

Although assignment is the core purpose, users still need to know whether assigned work has been completed.

**Other options considered**

- Overdue
- Skipped
- Partially completed
- Verified
- Completion analytics

These are unnecessary for the MVP.

---

# MVP Screens

The first version should contain four primary screens.

## 1. This Week

Main household view showing:

- chore
- assigned member
- completion status
- manual reassignment action

This should be the default screen.

## 2. Chores

Users can:

- add chores
- edit chores
- delete chores

## 3. Members

Users can:

- add household members
- remove household members

## 4. Settings

Users can configure:

- household name
- weekly rotation day

Manual reassignment should happen directly from **This Week**, not on a separate screen.

---

# Out of Scope for the MVP

The following features should not be included initially:

- points
- rewards
- streaks
- reminders
- notifications
- chore difficulty weighting
- workload optimization
- availability calendars
- member preferences
- automatic swapping
- voting
- comments
- chat
- analytics
- multiple chore frequencies
- AI-based assignment
- household expense tracking

These features could become later iterations, but they do not need to be solved to test the core idea.

---

# Core Product Hypothesis

The MVP should test one main question:

> **Is automatic weekly chore rotation useful enough to replace manually deciding who does what?**

---

# MVP Summary

> **A shared household app where chores are automatically assigned to members every week using simple turn-taking, with basic completion tracking and manual reassignment by any member.**
