#!/usr/bin/perl -w

# The Meffert challenge is a dodecahedron -- 12 pentagonal faces.
# If you break it apart there 4 spokes extending out from the center
# to present 4 "corner" pieces with 3 faces each, covering all 12 colors.
# It follows that there is a "correct" orientation for each of these
# corners and a decent strategy for solving would involve discovering
# maneuvers that maintain the correctness for each of the 4 spokes.

# This script identifies maneuvers that will move the large pentagonal
# "side" pieces around -- there are 6 of these pieces with two "sides"
# on each (ignore the 2 rhombi attached to these side pieces).
# The mappings $u, $v, $w, $x represent a clockwise turn of the spokes,
# $u is the Red/Orange/Yellow spoke (so for example, it moves the Red
# "side" through the proper locations of the Orange and Yellow "sides"
# and back to Red in 3 successive clockwise turns. It similarly
# impacts the location of the 3 sides that are attached to these, and
# has no impact whatsoever on the location of the other 6 sides
# relative to the spokes.
# $v is a rotation of Blue/Hot Pink/Dull Pink,
# $w is a rotation of Green/White/Purple, and
# $x is a rotation of Teal/Tan/Light Green.
# In the final notation exposed by the script, $u is annotated by 0,
# $u * $u (same as $u^-1) is annotated by 4, and similarly
# $v is 1, $v $v is 5, $w is 2, $w $w is 6, $x is 3, $x $x is 7.

my $u = {
  'Red' => 'Orange',
  'Purple' => 'Light Green',
  'Yellow' => 'Red',
  'Blue' => 'Purple',
  'Orange' => 'Yellow',
  'Light Green' => 'Blue',
  'Green' => 'Green',
  'Teal' => 'Teal',
  'Hot Pink' => 'Hot Pink',
  'White' => 'White',
  'Tan' => 'Tan',
  'Dull Pink' => 'Dull Pink',
};

my $v = {
  'Blue' => 'Hot Pink',
  'Hot Pink' => 'Dull Pink',
  'Dull Pink' => 'Blue',
  'Yellow' => 'Tan',
  'Tan' => 'Green',
  'Green' => 'Yellow',
  'Red' => 'Red',
  'Light Green' => 'Light Green',
  'White' => 'White',
  'Teal' => 'Teal',
  'Purple' => 'Purple',
  'Orange' => 'Orange',
};

my $w = {
  'Green' => 'White',
  'Purple' => 'Green',
  'White' => 'Purple',
  'Dull Pink' => 'Teal',
  'Red' => 'Dull Pink',
  'Teal' => 'Red',
  'Blue' => 'Blue',
  'Tan' => 'Tan',
  'Orange' => 'Orange',
  'Hot Pink' => 'Hot Pink',
  'Light Green' => 'Light Green',
  'Yellow' => 'Yellow',
};

my $x = {
  'Light Green' => 'Teal',
  'Teal' => 'Tan',
  'Tan' => 'Light Green',
  'Orange' => 'White',
  'White' => 'Hot Pink',
  'Hot Pink' => 'Orange',
  'Dull Pink' => 'Dull Pink',
  'Yellow' => 'Yellow',
  'Purple' => 'Purple',
  'Red' => 'Red',
  'Green' => 'Green',
  'Blue' => 'Blue',
};

sub convert_to_base_n($$) {
  my $n = shift;
  my $val = shift;
  my $output = '';
  while ($val > 0) {
    my $digit = $val % $n;
    $output = $digit.$output;
    $val = ($val - $digit) / $n;
  }
  return $output;
}

sub compute_transform($) {
  my $str = shift;
  my %mapping = ();
  foreach my $k (keys %$x) {
    $mapping{$k} = $k;
  }
  my @maps = ($u, $v, $w, $x);
  while ($str =~ s/\A(.)//xms) {
    my $fn = $maps[$1];
    foreach my $k (keys %$x) {
      $mapping{$k} = $fn->{$mapping{$k}};
    }
  }
  return {%mapping};
}

my %solution = ();
# We build every base 5 integer up to 12 digits, remove
# all the combos with 0s or any digit that doesn't occur
# 3, 6, or 9 times, then decrement each digit and analyze
# the impact of that sequence of moves on all the side pieces.
for (my $i = 0; $i < 5 ** 12; ++$i) {
  my $str = convert_to_base_n(5, $i);
  my @ccount = (0, 0, 0, 0);
  my $cpystr = $str;
  while ($str =~ s/\A(.)//xms) {
    ++$ccount[$1];
  }
  $str = $cpystr;

  # Skip numbers with 0 in them.
  next if $str =~ /0/;
  my $totalmod = 0;
  foreach my $c (@ccount) {
    $totalmod += $c % 3;
  }
  # Every digit has to show up 3, 6, or 9 times.
  next if $totalmod > 0;

  $str =~ s/1/0/g;
  $str =~ s/2/1/g;
  $str =~ s/3/2/g;
  $str =~ s/4/3/g;
  my $transform = compute_transform($str);
  my $diff = 0;
  foreach my $color (sort keys %$transform) {
    my $t = $transform->{$color};
    if ($t ne $color) {
      ++$diff;
    }
  }
  if ($diff > 0 && $diff < 7) {
    $str =~ s/000//;
    $str =~ s/111//;
    $str =~ s/222//;
    $str =~ s/333//;
    $str =~ s/00/4/g;
    $str =~ s/11/5/g;
    $str =~ s/22/6/g;
    $str =~ s/33/7/g;
    my $serialize = '';
    # print "$str:\n";
    foreach my $color (sort keys %$transform) {
      my $t = $transform->{$color};
      if ($t ne $color) {
        $serialize .= "  $color: $t\n";
        # print "    $color => $t\n";
      }
    }
    # If this is the quickest way we've seen, write that down.
    if (!exists $solution{$serialize} ||
        length($str) < length($solution{$serialize})) {
      $solution{$serialize} = $str;
    }
  }
}
# Dump all the shortest paths we identified for each permutation.
# Yes, there are some permutations that we missed because they
# needed more than 12 moves.
foreach my $serialize (sort keys %solution) {
  my $str = $solution{$serialize};
  print "$str:\n$serialize\n";
}
